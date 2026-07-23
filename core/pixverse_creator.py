import random
import re
import string
import time
import requests
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys

# ========== CONSTANTS ==========
EMAIL_WAIT_TIME = 90
TEMP_MAIL_API_BASE = "https://temp-mail.ai/api/mailbox"
PIXVERSE_REG_URL = "https://app.pixverse.ai/register"

OTP_INPUT_CSS = 'input[placeholder="Verification code"]'
OTP_BUTTON_CSS = 'button[type="submit"]'


def is_connected() -> bool:
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.RequestException:
        return False


# ========== EMAIL FUNCTIONS ==========
def get_temp_email(session: requests.Session) -> str:
    """Create a new temporary email via temp-mail.ai."""
    resp = session.post(f"{TEMP_MAIL_API_BASE}/random", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise Exception("Failed to get temporary email from temp-mail.ai")
    
    return data.get("email")


def check_inbox(session: requests.Session, email: str, wait: int = 90, stop_check=None) -> dict:
    """Poll temp-mail.ai inbox for email verification."""
    safe_email = requests.utils.quote(email)
    url = f"{TEMP_MAIL_API_BASE}/{safe_email}/messages"
    
    for _ in range(wait):
        if stop_check and stop_check():
            return None
        time.sleep(2)
        try:
            resp = session.get(url, timeout=10)
            data = resp.json()
            if data.get("success") and data.get("messages"):
                msg = data.get("messages")[0]
                # If no body content, fetch detail
                if not msg.get("text") and not msg.get("html"):
                    msg_id = msg.get("id")
                    detail_url = f"{TEMP_MAIL_API_BASE}/{safe_email}/message/{msg_id}"
                    detail_resp = session.get(detail_url, timeout=10)
                    detail_data = detail_resp.json()
                    if detail_data.get("success"):
                        return detail_data.get("message")
                return msg
        except requests.RequestException:
            pass
    return None


def extract_otp(message: dict) -> str:
    """Extract 6-digit OTP code from email subject or body."""
    if not message:
        return None
    candidates = [
        message.get('text', ''),
        message.get('html', ''),
        message.get('subject', '')
    ]
    for txt in candidates:
        if txt:
            matches = re.findall(r'\b(\d{6})\b', txt)
            if matches:
                return matches[0]
    return None


# ========== DOM INTERACTION FUNCTIONS ==========
def random_username(length: int = 10) -> str:
    return "user_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def random_password(length: int = 12) -> str:
    """Generate password acak: huruf besar + kecil + angka + simbol."""
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + "!@#$%^&*"
    pwd = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice("!@#$%^&*"),
    ]
    pwd += random.choices(chars, k=length - 4)
    random.shuffle(pwd)
    return "".join(pwd)


def react_fill(driver, element, value: str) -> str:
    """Fill input field triggering React/Vue events to update state."""
    driver.execute_script("arguments[0].focus();", element)
    time.sleep(0.3)
    driver.execute_script("arguments[0].value = '';", element)
    driver.execute_script("""
        var el = arguments[0];
        var val = arguments[1];
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
        ).set;
        nativeInputValueSetter.call(el, val);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    """, element, value)
    time.sleep(0.2)
    
    actual = driver.execute_script("return arguments[0].value;", element)
    if actual != value:
        element.click()
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.DELETE)
        time.sleep(0.1)
        for char in value:
            element.send_keys(char)
            time.sleep(0.02)
            
    return driver.execute_script("return arguments[0].value;", element)


def fill_otp_inputs(driver, otp_code: str) -> bool:
    wait = WebDriverWait(driver, 15)
    try:
        el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, OTP_INPUT_CSS)))
        if el.is_displayed():
            react_fill(driver, el, otp_code)
            return True
    except Exception:
        pass
        
    otp_boxes = driver.find_elements(
        By.CSS_SELECTOR,
        'input[maxlength="1"], input[data-index], .ant-otp input'
    )
    otp_boxes = [el for el in otp_boxes if el.is_displayed()]
    
    if len(otp_boxes) >= len(otp_code):
        for i, char in enumerate(otp_code):
            try:
                otp_boxes[i].click()
                time.sleep(0.1)
                otp_boxes[i].send_keys(char)
                time.sleep(0.15)
            except Exception:
                pass
        return True
        
    single_selectors = [
        'input[placeholder*="code" i]',
        'input[placeholder*="Code" i]',
        'input[placeholder*="OTP" i]',
        'input[placeholder*="otp" i]',
        'input[placeholder*="verification" i]',
        'input[type="number"][maxlength="6"]',
        'input[autocomplete="one-time-code"]',
    ]
    
    for sel in single_selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed():
                react_fill(driver, el, otp_code)
                return True
        except Exception:
            continue
            
    return False


def click_verify_button(driver) -> bool:
    try:
        btn = driver.find_element(By.CSS_SELECTOR, OTP_BUTTON_CSS)
        driver.execute_script("arguments[0].click();", btn)
        return True
    except Exception:
        pass
        
    fallback_selectors = [
        (By.XPATH, '//button[contains(., "Verify")]'),
        (By.XPATH, '//button[contains(., "Confirm")]'),
        (By.XPATH, '//button[contains(., "Submit")]'),
        (By.XPATH, '//button[contains(., "Continue")]'),
        (By.CSS_SELECTOR, 'button[type="submit"]'),
    ]
    
    for by, sel in fallback_selectors:
        try:
            btn = driver.find_element(by, sel)
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                return True
        except Exception:
            continue
            
    return False


class PixVerseAccountCreator:
    def __init__(self, log_callback=None, stop_check=None, driver_opened_callback=None):
        self.log = log_callback or print
        self.stop_check = stop_check
        self.driver_opened_callback = driver_opened_callback
        self.session = requests.Session()

    def _stopped(self) -> bool:
        return bool(self.stop_check and self.stop_check())

    def _make_driver(self):
        driver = Driver(
            uc=True,
            headless=False,
        )
        driver.set_window_size(1280, 720)
        return driver

    def _wait_for_registration_form(self, driver, timeout=15) -> bool:
        """Wait for the registration form (username field) to appear."""
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Username"]'))
            )
            return True
        except Exception:
            return False

    def create_account(self, index: int, password: str, max_retries: int = 2):
        for attempt in range(max_retries + 1):
            if self._stopped():
                return False, None, None

            driver = None
            try:
                driver = self._make_driver()
                if self.driver_opened_callback:
                    self.driver_opened_callback(driver)

                # ---- OPEN PAGE ----
                driver.uc_open_with_reconnect(PIXVERSE_REG_URL, reconnect_time=1)

                # ---- WAIT FOR REGISTRATION FORM ----
                if not self._wait_for_registration_form(driver, timeout=15):
                    driver.refresh()
                    time.sleep(3)
                    driver.uc_open_with_reconnect(PIXVERSE_REG_URL, reconnect_time=1)
                    if not self._wait_for_registration_form(driver, timeout=15):
                        raise Exception("Registration form did not appear after refresh")

                # ---- GET TEMP EMAIL ----
                email = get_temp_email(self.session)
                if not email:
                    raise Exception("Failed to get temporary email")

                username = random_username()

                # ---- FILL REGISTRATION FORM ----
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Username"]'))
                )
                time.sleep(1.5)

                if self._stopped():
                    raise Exception("Stop requested")

                fields = [
                    ('input[placeholder="Username"]', username),
                    ('input[placeholder="Email"]', email),
                    ('input[placeholder="Password"]', password),
                    ('input[placeholder="Confirm password"]', password),
                ]
                
                for sel, val in fields:
                    if self._stopped():
                        raise Exception("Stop requested")
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                    react_fill(driver, el, val)

                # ---- CLICK CONTINUE ----
                continue_btn = None
                btn_selectors = [
                    (By.XPATH, '//button[contains(., "Continue")]'),
                    (By.XPATH, '//button[.//span[contains(text(),"Continue")]]'),
                    (By.CSS_SELECTOR, 'button[type="submit"]'),
                ]
                
                for by, sel in btn_selectors:
                    try:
                        btn = driver.find_element(by, sel)
                        if btn.is_displayed():
                            continue_btn = btn
                            break
                    except Exception:
                        continue

                if not continue_btn:
                    raise Exception("Continue button not found")

                if self._stopped():
                    raise Exception("Stop requested")

                driver.execute_script("arguments[0].click();", continue_btn)

                # ---- WAIT FOR OTP PAGE ----
                otp_page_detected = False
                for _ in range(15):
                    if self._stopped():
                        raise Exception("Stop requested")
                    time.sleep(1)
                    current_url = driver.current_url.lower()
                    page_src = driver.page_source.lower()
                    
                    if any(kw in current_url for kw in ['verify', 'otp', 'code', 'verification']) or \
                       any(kw in page_src for kw in ['verify', 'enter the code', 'check your email', 'sent a code']):
                        otp_page_detected = True
                        break

                # ---- POLL FOR OTP EMAIL ----
                self.log(f"[Akun {index}] Menunggu kode OTP...")
                msg = check_inbox(self.session, email, wait=EMAIL_WAIT_TIME, stop_check=self.stop_check)
                if not msg:
                    raise Exception("OTP Email not received - timeout!")

                otp_code = extract_otp(msg)
                if not otp_code:
                    raise Exception("Failed to extract OTP code from email!")

                self.log(f"[Akun {index}] Kode OTP diterima: {otp_code}")

                if self._stopped():
                    raise Exception("Stop requested")

                # ---- FILL OTP ----
                if not fill_otp_inputs(driver, otp_code):
                    raise Exception("Failed to input OTP into the page!")

                time.sleep(1)
                if self._stopped():
                    raise Exception("Stop requested")

                # ---- CLICK VERIFY ----
                if not click_verify_button(driver):
                    raise Exception("Verify button not found!")

                # ---- WAIT FOR DASHBOARD REDIRECT ----
                login_success = False
                for _ in range(20):
                    if self._stopped():
                        raise Exception("Stop requested")
                    time.sleep(1)
                    current_url = driver.current_url.lower()
                    if any(kw in current_url for kw in ['home', 'dashboard', 'create', 'studio', 'app']):
                        if 'register' not in current_url and 'verify' not in current_url:
                            login_success = True
                            break

                if login_success:
                    return True, email, driver
                else:
                    raise Exception("Registration completed but automatic login redirect was not detected")

            except Exception as e:
                # If stopped explicitly, don't spam errors
                if self._stopped():
                    return False, None, None
                    
                self.log(f"[Akun {index}] Percobaan {attempt + 1} gagal: {str(e)[:100]}")
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                        
                if attempt == max_retries:
                    return False, None, None
                time.sleep(random.uniform(3, 7))

        return False, None, None
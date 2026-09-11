import random
import time
from typing import Callable, Optional, Tuple

import requests
from config import EMAIL_WAIT_TIMEOUT, PIXVERSE_REG_URL
from core.mail_service import check_inbox, extract_otp, get_temp_email, random_username
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumbase import Driver


def react_fill(driver, element, value: str) -> str:
    """Fill input field triggering React/Vue native setter and input/change events."""
    driver.execute_script("arguments[0].focus();", element)
    time.sleep(0.3)
    driver.execute_script("arguments[0].value = '';", element)
    driver.execute_script(
        """
        var el = arguments[0];
        var val = arguments[1];
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
        ).set;
        nativeInputValueSetter.call(el, val);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    """,
        element,
        value,
    )
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
    """Find OTP input fields (single input or multi-box) and insert OTP."""
    wait = WebDriverWait(driver, 15)
    try:
        el = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Verification code"]'))
        )
        if el.is_displayed():
            react_fill(driver, el, otp_code)
            return True
    except Exception:
        pass

    otp_boxes = driver.find_elements(
        By.CSS_SELECTOR, 'input[maxlength="1"], input[data-index], .ant-otp input'
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
    """Locate and click OTP verification submission button."""
    try:
        btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
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
    """Creates PixVerse accounts using undetected Chrome with temporary email verification."""

    def __init__(
        self,
        log_callback: Optional[Callable[[str], None]] = None,
        stop_check: Optional[Callable[[], bool]] = None,
        driver_opened_callback: Optional[Callable[[Driver], None]] = None,
    ):
        self.log = log_callback or print
        self.stop_check = stop_check
        self.driver_opened_callback = driver_opened_callback
        self.session = requests.Session()

    def _stopped(self) -> bool:
        return bool(self.stop_check and self.stop_check())

    def _make_driver(self) -> Driver:
        driver = Driver(uc=True, headless=False)
        driver.set_window_size(1280, 720)
        return driver

    def _wait_for_registration_form(self, driver, timeout: int = 15) -> bool:
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Username"]'))
            )
            return True
        except Exception:
            return False

    def create_account(
        self,
        index: int,
        password: str,
        max_retries: int = 2,
    ) -> Tuple[bool, Optional[str], Optional[Driver]]:
        """
        Execute full registration flow for a single account.
        Returns (success, email, driver).
        """
        for attempt in range(max_retries + 1):
            if self._stopped():
                return False, None, None

            driver = None
            try:
                driver = self._make_driver()
                if self.driver_opened_callback:
                    self.driver_opened_callback(driver)

                # 1. Buka Halaman Registrasi
                driver.uc_open_with_reconnect(PIXVERSE_REG_URL, reconnect_time=1)

                if not self._wait_for_registration_form(driver, timeout=15):
                    driver.refresh()
                    time.sleep(3)
                    driver.uc_open_with_reconnect(PIXVERSE_REG_URL, reconnect_time=1)
                    if not self._wait_for_registration_form(driver, timeout=15):
                        raise Exception("Formulir pendaftaran tidak muncul setelah refresh")

                # 2. Dapatkan Email Sementara
                email = get_temp_email(self.session)
                if not email:
                    raise Exception("Gagal mendapatkan email sementara")

                username = random_username()

                # 3. Isi Formulir Registrasi
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Username"]'))
                )
                time.sleep(1.5)

                if self._stopped():
                    raise Exception("Proses dihentikan pengguna")

                fields = [
                    ('input[placeholder="Username"]', username),
                    ('input[placeholder="Email"]', email),
                    ('input[placeholder="Password"]', password),
                    ('input[placeholder="Confirm password"]', password),
                ]

                for sel, val in fields:
                    if self._stopped():
                        raise Exception("Proses dihentikan pengguna")
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                    react_fill(driver, el, val)

                # 4. Klik Continue
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
                    raise Exception("Tombol Continue tidak ditemukan")

                if self._stopped():
                    raise Exception("Proses dihentikan pengguna")

                driver.execute_script("arguments[0].click();", continue_btn)

                # 5. Tunggu Halaman OTP
                self.log(f"[Akun {index}] Menunggu kode OTP...")
                msg = check_inbox(
                    self.session,
                    email,
                    wait=EMAIL_WAIT_TIMEOUT,
                    stop_check=self.stop_check,
                )
                if not msg:
                    raise Exception("Timeout menunggu email OTP!")

                otp_code = extract_otp(msg)
                if not otp_code:
                    raise Exception("Gagal mengekstrak 6 digit OTP dari email!")

                self.log(f"[Akun {index}] Kode OTP diterima: {otp_code}")

                if self._stopped():
                    raise Exception("Proses dihentikan pengguna")

                # 6. Masukkan OTP & Verifikasi
                if not fill_otp_inputs(driver, otp_code):
                    raise Exception("Gagal memasukkan kode OTP ke halaman!")

                time.sleep(1)
                if self._stopped():
                    raise Exception("Proses dihentikan pengguna")

                if not click_verify_button(driver):
                    raise Exception("Tombol verifikasi tidak ditemukan!")

                # 7. Tunggu Redirect ke Dashboard
                login_success = False
                for _ in range(20):
                    if self._stopped():
                        raise Exception("Proses dihentikan pengguna")
                    time.sleep(1)
                    current_url = driver.current_url.lower()
                    if any(kw in current_url for kw in ["home", "dashboard", "create", "studio", "app"]):
                        if "register" not in current_url and "verify" not in current_url:
                            login_success = True
                            break

                if login_success:
                    return True, email, driver
                else:
                    raise Exception("Registrasi selesai tetapi redirect ke dashboard tidak terdeteksi")

            except Exception as e:
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

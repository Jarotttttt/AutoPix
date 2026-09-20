import random
import time
from typing import Callable, Optional, Tuple

from config import PIXVERSE_REG_URL, REGISTRATION_TIMEOUT
from core.mail_service import TempTFMailService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumbase import Driver
from utils.helpers import random_password, random_username


def react_fill(driver, element, value: str) -> str:
    """Fill input field triggering React/Vue synthetic events safely."""
    driver.execute_script("arguments[0].focus();", element)
    time.sleep(0.2)
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
    """Find OTP input boxes (single input or multi-box) and type OTP code."""
    # 1. Cek multi-box input (1 kotak per digit)
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
                time.sleep(0.1)
            except Exception:
                pass
        return True

    # 2. Cek single input verification code
    single_selectors = [
        'input[placeholder*="Verification" i]',
        'input[placeholder*="code" i]',
        'input[placeholder*="OTP" i]',
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
    """Click submit button on OTP verification step."""
    btn_selectors = [
        (By.CSS_SELECTOR, 'button[type="submit"]'),
        (By.XPATH, '//button[contains(., "Verify")]'),
        (By.XPATH, '//button[contains(., "Confirm")]'),
        (By.XPATH, '//button[contains(., "Continue")]'),
    ]

    for by, sel in btn_selectors:
        try:
            btns = driver.find_elements(by, sel)
            for btn in btns:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    return True
        except Exception:
            continue

    return False


class AccountCreatorService:
    """Manages autonomous registration on PixVerse with Temp.tf email & UC driver."""

    def __init__(
        self,
        log_callback: Optional[Callable[[str], None]] = None,
        stop_check: Optional[Callable[[], bool]] = None,
        driver_tracker: Optional[Callable[[Driver], None]] = None,
    ):
        self.log = log_callback or print
        self.stop_check = stop_check
        self.driver_tracker = driver_tracker
        self.mail_service = TempTFMailService()

    def _is_stopped(self) -> bool:
        return bool(self.stop_check and self.stop_check())

    def _create_driver(self) -> Driver:
        driver = Driver(uc=True, headless=False)
        driver.set_window_size(1280, 800)
        return driver

    def create_account(
        self,
        index: int,
        max_retries: int = 2,
    ) -> Tuple[bool, Optional[str], Optional[Driver]]:
        """
        Creates a new verified PixVerse account.
        Returns: (success, email, driver_instance)
        """
        for attempt in range(1, max_retries + 2):
            if self._is_stopped():
                return False, None, None

            driver = None
            try:
                self.log(f"[Akun #{index}] Membuka browser undetected (Percobaan {attempt})...")
                driver = self._create_driver()
                if self.driver_tracker:
                    self.driver_tracker(driver)

                # 1. Buka formulir registrasi PixVerse
                driver.uc_open_with_reconnect(PIXVERSE_REG_URL, reconnect_time=2)

                wait = WebDriverWait(driver, REGISTRATION_TIMEOUT)
                form_present = False
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Username"]')))
                    form_present = True
                except Exception:
                    # Retry buka halaman jika kena Cloudflare interstitial
                    driver.refresh()
                    time.sleep(3)
                    driver.uc_open_with_reconnect(PIXVERSE_REG_URL, reconnect_time=2)
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Username"]')))
                    form_present = True

                if not form_present:
                    raise RuntimeError("Formulir pendaftaran PixVerse gagal dimuat.")

                # 2. Dapatkan temp mail dari temp.tf (@high.edu.pl / Outlook)
                self.log(f"[Akun #{index}] Mengambil email disposable dari temp.tf...")
                email = self.mail_service.create_inbox()
                username = random_username("user_")
                password = random_password(12)

                self.log(f"[Akun #{index}] Mengisi data registrasi ({email})...")
                time.sleep(1)

                fields = [
                    ('input[placeholder="Username"]', username),
                    ('input[placeholder="Email"]', email),
                    ('input[placeholder="Password"]', password),
                    ('input[placeholder="Confirm password"]', password),
                ]

                for sel, val in fields:
                    if self._is_stopped():
                        raise InterruptedError("Proses dibatalkan.")
                    elem = driver.find_element(By.CSS_SELECTOR, sel)
                    react_fill(driver, elem, val)
                    time.sleep(0.1)

                # 3. Klik Continue / Submit
                continue_btn = None
                btn_candidates = [
                    (By.XPATH, '//button[contains(., "Continue")]'),
                    (By.XPATH, '//button[.//span[contains(text(),"Continue")]]'),
                    (By.CSS_SELECTOR, 'button[type="submit"]'),
                ]
                for by, sel in btn_candidates:
                    try:
                        btn = driver.find_element(by, sel)
                        if btn.is_displayed():
                            continue_btn = btn
                            break
                    except Exception:
                        continue

                if not continue_btn:
                    raise RuntimeError("Tombol Continue tidak ditemukan pada form registrasi.")

                driver.execute_script("arguments[0].click();", continue_btn)

                # 4. Polling OTP dari temp.tf
                self.log(f"[Akun #{index}] Menunggu kode OTP PixVerse masuk ke inbox...")
                otp_code = self.mail_service.poll_for_otp(
                    email=email,
                    stop_check=self.stop_check,
                    log_callback=self.log,
                )
                self.log(f"[Akun #{index}] Kode OTP berhasil diperoleh: {otp_code}")

                if self._is_stopped():
                    raise InterruptedError("Proses dibatalkan.")

                # 5. Isi kode OTP & Verifikasi
                time.sleep(1)
                if not fill_otp_inputs(driver, otp_code):
                    raise RuntimeError("Gagal memasukkan kode OTP ke input.")

                time.sleep(0.8)
                click_verify_button(driver)

                # 6. Verifikasi Login Sukses (Redirect dari form registrasi)
                success = False
                for _ in range(15):
                    if self._is_stopped():
                        raise InterruptedError("Proses dibatalkan.")
                    time.sleep(1)
                    curr = driver.current_url.lower()
                    if any(kw in curr for kw in ["home", "creation", "studio", "dashboard", "app.pixverse.ai"]):
                        if "register" not in curr and "verify" not in curr:
                            success = True
                            break

                if success:
                    self.log(f"[Akun #{index}] Registrasi & Verifikasi BERHASIL! ({email})")
                    return True, email, driver
                else:
                    raise RuntimeError("Registrasi terkirim tapi redirect login tidak terdeteksi.")

            except Exception as e:
                if self._is_stopped():
                    if driver:
                        try:
                            driver.quit()
                        except Exception:
                            pass
                    return False, None, None

                self.log(f"[Akun #{index}] Percobaan {attempt} gagal: {e}")
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass

                if attempt <= max_retries:
                    time.sleep(random.uniform(3, 6))

        return False, None, None

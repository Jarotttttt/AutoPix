import time
from typing import Callable, Optional

from config import (
    CONCURRENT_LIMIT_MAX_RETRIES,
    CONCURRENT_LIMIT_WAIT_SECONDS,
    PIXVERSE_VIDEO_URL,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

PROMPT_SELECTOR = 'textarea[placeholder*="Describe the content"]'

PROMPT_JS = """
return Array.from(document.querySelectorAll('textarea')).find(function(t) {
    return t.placeholder.indexOf('Describe the content') !== -1
        || (t.offsetParent !== null && t.placeholder === '');
});
"""

CREATE_BTN_JS = """
return Array.from(document.querySelectorAll('button')).find(function(b) {
    var txt = b.textContent.trim();
    return txt.startsWith('Create') && !txt.startsWith('Created');
});
"""

SWITCHES_JS = "return Array.from(document.querySelectorAll('button[role=\"switch\"]'));"

TOGGLE_JS = """
var btn = arguments[0];
btn.focus();
btn.click();
"""

REACT_TEXTAREA_SETTER = """
var el = arguments[0];
var val = arguments[1];
var nativeSetter = Object.getOwnPropertyDescriptor(
    window.HTMLTextAreaElement.prototype, 'value'
).set;
nativeSetter.call(el, val);
el.dispatchEvent(new Event('input', {bubbles: true}));
el.dispatchEvent(new Event('change', {bubbles: true}));
"""


class PixVerseVideoGenerator:
    """Automates video creation on PixVerse via Selenium WebDriver."""

    def __init__(
        self,
        driver,
        log_callback: Optional[Callable[[str], None]] = None,
        stop_check: Optional[Callable[[], bool]] = None,
    ):
        self.driver = driver
        self.log = log_callback or print
        self.stop_check = stop_check or (lambda: False)
        self.wait = WebDriverWait(driver, 20)

    def _stopped(self) -> bool:
        return bool(self.stop_check())

    def _js(self, script, *args):
        return self.driver.execute_script(script, *args)

    def _get_textarea(self):
        # 1. CSS selector langsung
        try:
            el = self.driver.find_element(By.CSS_SELECTOR, PROMPT_SELECTOR)
            if el and el.is_displayed():
                return el
        except Exception:
            pass

        # 2. JavaScript fallback
        try:
            el = self._js(PROMPT_JS)
            if el:
                return el
        except Exception:
            pass

        # 3. Textarea visible manapun
        try:
            for ta in self.driver.find_elements(By.TAG_NAME, "textarea"):
                try:
                    if ta.is_displayed():
                        return ta
                except Exception:
                    continue
        except Exception:
            pass

        return None

    def _wait_for_textarea(self, timeout: int = 15):
        deadline = time.time() + timeout
        while time.time() < deadline:
            el = self._get_textarea()
            if el:
                return el
            time.sleep(0.5)
        self.log("  ⚠️ Textarea prompt tidak ditemukan")
        return None

    def _get_switches(self):
        try:
            switches = self._js(SWITCHES_JS)
            return switches or []
        except Exception:
            return []

    def _switch_is_on(self, switch_el) -> bool:
        try:
            return switch_el.get_attribute("aria-checked") == "true"
        except Exception:
            return False

    def _turn_off_switch(self, switch_el, label="switch") -> bool:
        for _ in range(3):
            if not self._switch_is_on(switch_el):
                return True
            try:
                self._js(TOGGLE_JS, switch_el)
            except Exception:
                pass
            time.sleep(0.5)

        if not self._switch_is_on(switch_el):
            return True
        self.log(f"  ⚠️ {label} gagal dimatikan")
        return False

    def navigate_to_creation(self):
        try:
            current = self.driver.current_url
        except Exception:
            current = ""

        if "app.pixverse.ai" not in current or "/creation" not in current:
            self.driver.get(PIXVERSE_VIDEO_URL)
            time.sleep(3)

    def disable_audio(self) -> bool:
        switches = self._get_switches()
        if not switches:
            return False
        return self._turn_off_switch(switches[0], label="Audio")

    def disable_multi_shot(self) -> bool:
        switches = self._get_switches()
        if len(switches) < 2:
            return False
        return self._turn_off_switch(switches[1], label="Multi-Shot")

    def type_prompt(self, prompt_text: str):
        textarea = self._wait_for_textarea()
        if not textarea:
            raise RuntimeError("Prompt textarea tidak ditemukan")

        self.log("  Menulis prompt...")

        # Method 1: React setter
        try:
            self._js(REACT_TEXTAREA_SETTER, textarea, prompt_text)
            time.sleep(0.4)
            actual = textarea.get_attribute("value") or ""
            if prompt_text[:10] in actual:
                return textarea
        except Exception:
            pass

        # Method 2: Key strokes
        try:
            self._js("arguments[0].focus();", textarea)
            time.sleep(0.2)
            textarea.send_keys(Keys.CONTROL + "a")
            time.sleep(0.1)
            textarea.send_keys(Keys.DELETE)
            time.sleep(0.1)
            textarea.send_keys(prompt_text)
            time.sleep(0.3)
            actual = textarea.get_attribute("value") or ""
            if prompt_text[:10] in actual:
                return textarea
        except Exception:
            pass

        # Method 3: Character by character
        try:
            self._js("arguments[0].click(); arguments[0].select();", textarea)
            time.sleep(0.2)
            for char in prompt_text:
                textarea.send_keys(char)
            time.sleep(0.3)
            return textarea
        except Exception as e:
            raise RuntimeError(f"Gagal menulis prompt: {e}")

    def _dismiss_popup(self) -> bool:
        POPUP_JS = """
        var modal = document.querySelector('.ant-modal-content, [class*="modal-content"]');
        if (!modal) return null;
        var txt = modal.innerText || '';
        if (txt.indexOf('concurrent') !== -1 || txt.indexOf('Maximum') !== -1 ||
            txt.indexOf('generation') !== -1 || txt.indexOf('Subscribe') !== -1) {
            return txt.substring(0, 200);
        }
        return null;
        """
        CLOSE_POPUP_JS = """
        var closeBtn = document.querySelector('.ant-modal-close, [aria-label="Close"], button.ant-modal-close-x');
        if (!closeBtn) {
            var btns = Array.from(document.querySelectorAll('button'));
            closeBtn = btns.find(function(b) {
                var cls = b.className || '';
                return cls.indexOf('close') !== -1 || cls.indexOf('modal-close') !== -1;
            });
        }
        if (closeBtn) { closeBtn.click(); return true; }
        return false;
        """
        try:
            popup_text = self._js(POPUP_JS)
            if popup_text:
                self.log("  ⏳ Terdeteksi limit antrean! Menutup popup...")
                closed = self._js(CLOSE_POPUP_JS)
                if closed:
                    time.sleep(1)
                    return True
                else:
                    self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    time.sleep(1)
                    return True
        except Exception:
            pass
        return False

    def click_create(self) -> bool:
        try:
            create_btn = self._js(CREATE_BTN_JS)
            if create_btn:
                self._js("arguments[0].click();", create_btn)
                return True
        except Exception:
            pass

        try:
            btns = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in btns:
                try:
                    txt = btn.text.strip()
                    if txt.startswith("Create") and not txt.startswith("Created"):
                        self._js("arguments[0].click();", btn)
                        return True
                except Exception:
                    continue
        except Exception:
            pass

        return False

    def generate_video(
        self,
        prompt_text: str,
        wait_seconds: int = 3,
        max_concurrent_retries: int = CONCURRENT_LIMIT_MAX_RETRIES,
        concurrent_wait: int = CONCURRENT_LIMIT_WAIT_SECONDS,
    ) -> bool:
        """Full generate flow with retry on concurrent limits."""
        try:
            if self._stopped():
                return False

            self.navigate_to_creation()
            if self._stopped():
                return False

            time.sleep(2)
            self.disable_audio()
            if self._stopped():
                return False

            self.disable_multi_shot()
            if self._stopped():
                return False

            self.type_prompt(prompt_text)
            if self._stopped():
                return False

            for attempt in range(max_concurrent_retries + 1):
                if self._stopped():
                    return False

                success = self.click_create()
                if not success:
                    return False

                time.sleep(2)
                popup_found = self._dismiss_popup()

                if not popup_found:
                    time.sleep(wait_seconds)
                    return True
                else:
                    if attempt < max_concurrent_retries:
                        self.log(
                            f"  ⏳ Limit antrean! Menunggu {concurrent_wait} detik sebelum mencoba kembali ({attempt + 1}/{max_concurrent_retries})..."
                        )
                        for _ in range(concurrent_wait):
                            if self._stopped():
                                return False
                            time.sleep(1)
                        self.type_prompt(prompt_text)
                    else:
                        self.log("  ✗ Gagal: Limit antrean terlampaui")
                        return False

            return False

        except Exception as e:
            self.log(f"  ✗ Gagal generate video: {e}")
            return False

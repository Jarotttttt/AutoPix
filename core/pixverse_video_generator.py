# -*- coding: utf-8 -*-
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys

PIXVERSE_URL = "https://app.pixverse.ai/creation/video"

# ─── Selectors discovered via Chrome DevTools live inspection ────────────────
#
# Prompt textarea (VISIBLE one):
#   placeholder: "Describe the content you want to create"
#   NOTE: ada textarea lain (hidden) dengan placeholder "Start with sentence..."
#   Gunakan: textarea[placeholder*="Describe the content"]
#
# Audio toggle (Ant Design Switch):
#   button[role="switch"] index 0
#   aria-checked="true" when ON, "false" when OFF
#   Parent label: "Audio"
#
# Multi-Shot toggle:
#   button[role="switch"] index 1
#   aria-checked="true" when ON, "false" when OFF
#   Parent label: "Multi-Shot"
#
# Create button:
#   button dengan text "Create<credits>"
#   Filter: button.textContent.trim().startsWith("Create") AND bukan "Created..."
#   Gunakan JS dengan filter: text == "Create" or startsWith("Create ") or match /^Create\d/
#
# Toggle method yang bekerja:
#   element.focus(); element.click() via execute_script
#
# ────────────────────────────────────────────────────────────────────────────────

# Textarea prompt yang VISIBLE
PROMPT_SELECTOR = 'textarea[placeholder*="Describe the content"]'

# Fallback: coba semua textarea dan ambil yang visible
PROMPT_JS = """
return Array.from(document.querySelectorAll('textarea')).find(function(t) {
    return t.placeholder.indexOf('Describe the content') !== -1
        || (t.offsetParent !== null && t.placeholder === '');
});
"""

# Create button: text starts with "Create" tapi bukan "Created"
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

# React-compatible value setter untuk textarea
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
    """
    Automates generating a video on PixVerse via Selenium.

    Flow:
      1. Navigate to /creation/video (if not already there)
      2. Wait for visible prompt textarea
      3. Disable Audio toggle (switch[0])
      4. Disable Multi-Shot toggle (switch[1])
      5. Type prompt into textarea via React-compatible setter
      6. Click the Create button
    """

    def __init__(self, driver, log_callback=None, stop_check=None):
        self.driver = driver
        self.log = log_callback or print
        self.stop_check = stop_check or (lambda: False)
        self.wait = WebDriverWait(driver, 20)

    # ──────────────────────────── helpers ────────────────────────────────────

    def _stopped(self):
        return bool(self.stop_check())

    def _js(self, script, *args):
        return self.driver.execute_script(script, *args)

    def _get_textarea(self):
        """Find the VISIBLE prompt textarea using CSS selector first, then JS fallback."""
        # Priority 1: CSS selector langsung
        try:
            el = self.driver.find_element(By.CSS_SELECTOR, PROMPT_SELECTOR)
            if el and el.is_displayed():
                return el
        except Exception:
            pass

        # Priority 2: via JavaScript (cari placeholder 'Describe the content')
        try:
            el = self._js(PROMPT_JS)
            if el:
                return el
        except Exception:
            pass

        # Priority 3: ambil textarea visible manapun (yang bukan hidden)
        try:
            all_ta = self.driver.find_elements(By.TAG_NAME, "textarea")
            for ta in all_ta:
                try:
                    if ta.is_displayed():
                        return ta
                except Exception:
                    continue
        except Exception:
            pass

        return None

    def _wait_for_textarea(self):
        """Wait up to 15s for prompt textarea to appear, then fallback."""
        deadline = time.time() + 15
        while time.time() < deadline:
            el = self._get_textarea()
            if el:
                return el
            time.sleep(0.5)
        self.log("  ⚠️ Textarea prompt tidak ditemukan")
        return None

    def _get_switches(self):
        """Return list of Ant-Design switch buttons (Audio=idx0, Multi-Shot=idx1)."""
        try:
            switches = self._js(SWITCHES_JS)
            return switches or []
        except Exception:
            return []

    def _switch_is_on(self, switch_el):
        """Return True if the switch is currently ON (checked)."""
        try:
            return switch_el.get_attribute("aria-checked") == "true"
        except Exception:
            return False

    def _turn_off_switch(self, switch_el, label="switch"):
        """Click the switch OFF if it is currently ON. Retries up to 3 times."""
        for attempt in range(3):
            if not self._switch_is_on(switch_el):
                return True
            try:
                self._js(TOGGLE_JS, switch_el)
            except Exception as e:
                pass
            time.sleep(0.5)
        # Final check
        if not self._switch_is_on(switch_el):
            return True
        self.log(f"  ⚠️ {label} gagal dimatikan")
        return False

    # ──────────────────────────── main flow ──────────────────────────────────

    def navigate_to_home(self):
        """Navigate to PixVerse creation page if not already there."""
        try:
            current = self.driver.current_url
        except Exception:
            current = ""

        if "app.pixverse.ai" not in current:
            self.driver.get(PIXVERSE_URL)
            time.sleep(3)
        else:
            # Jika sudah di pixverse, pastikan di halaman creation
            if "/creation" not in current:
                self.driver.get(PIXVERSE_URL)
                time.sleep(3)

    def disable_audio(self):
        """Ensure the Audio toggle (switch index 0) is OFF."""
        switches = self._get_switches()
        if not switches:
            return False
        return self._turn_off_switch(switches[0], label="Audio")

    def disable_multi_shot(self):
        """Ensure the Multi-Shot toggle (switch index 1) is OFF."""
        switches = self._get_switches()
        if len(switches) < 2:
            return False
        return self._turn_off_switch(switches[1], label="Multi-Shot")

    def type_prompt(self, prompt_text: str):
        """Clear existing text and type the prompt into the visible textarea."""
        textarea = self._wait_for_textarea()
        if not textarea:
            raise RuntimeError("Prompt textarea tidak ditemukan")

        self.log(f"  Menulis prompt...")

        # Method 1: React native setter (paling kompatibel dengan React controlled inputs)
        try:
            self._js(REACT_TEXTAREA_SETTER, textarea, prompt_text)
            time.sleep(0.4)
            actual = textarea.get_attribute("value") or ""
            if prompt_text[:10] in actual:
                return textarea
        except Exception as e:
            pass

        # Method 2: Click + select all + send keys
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
        except Exception as e:
            pass

        # Method 3: Click textarea, select all dengan JS, lalu type character by character
        try:
            self._js("arguments[0].click(); arguments[0].select();", textarea)
            time.sleep(0.2)
            for char in prompt_text:
                textarea.send_keys(char)
            time.sleep(0.3)
            return textarea
        except Exception as e:
            raise RuntimeError(f"Gagal menulis prompt (semua method gagal): {e}")

    def _dismiss_popup(self):
        """
        Cek dan tutup popup 'Maximum concurrent generations reached'.
        Return True jika popup ditemukan dan berhasil ditutup.
        """
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
            // Coba cari tombol X atau close di dalam modal
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
                    # Fallback: tekan Escape
                    self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(1)
                    return True
        except Exception as e:
            pass
        return False

    def click_create(self):
        """Find and click the Create button (bukan Created)."""
        # Method 1: via JavaScript (lebih akurat untuk filter text)
        try:
            create_btn = self._js(CREATE_BTN_JS)
            if create_btn:
                self._js("arguments[0].click();", create_btn)
                return True
        except Exception as e:
            pass

        # Method 2: via Selenium find_elements
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
        except Exception as e:
            pass

        return False

    def generate_video(self, prompt_text: str, wait_seconds: int = 5,
                        max_concurrent_retries: int = 3, concurrent_wait: int = 30):
        """
        Full flow: navigate → disable Audio → disable Multi-Shot → type prompt → click Create.
        Jika popup 'Maximum concurrent generations reached' muncul, tutup dan retry.

        :param prompt_text:              Teks deskripsi video
        :param wait_seconds:             Detik tunggu setelah klik Create berhasil
        :param max_concurrent_retries:   Maks retry jika kena concurrent limit popup
        :param concurrent_wait:          Detik tunggu sebelum retry (default 30s)
        :returns:                        True jika Create berhasil diklik
        """
        try:
            if self._stopped():
                return False

            # 1. Navigate
            self.navigate_to_home()
            if self._stopped():
                return False

            # 2. Tunggu halaman siap
            time.sleep(2)

            # 3. Disable Audio
            self.disable_audio()
            if self._stopped():
                return False

            # 4. Disable Multi-Shot
            self.disable_multi_shot()
            if self._stopped():
                return False

            # 5. Type prompt
            self.type_prompt(prompt_text)
            if self._stopped():
                return False

            # 6. Click Create, dengan retry jika kena concurrent limit
            for attempt in range(max_concurrent_retries + 1):
                if self._stopped():
                    return False

                success = self.click_create()

                if not success:
                    return False

                # Cek apakah muncul popup concurrent limit (tunggu 2s dulu)
                time.sleep(2)
                popup_found = self._dismiss_popup()

                if not popup_found:
                    # Tidak ada popup = generate berhasil masuk antrian
                    time.sleep(wait_seconds)
                    return True
                else:
                    # Ada popup concurrent limit
                    if attempt < max_concurrent_retries:
                        self.log(
                            f"  ⏳ Limit antrean! Menunggu {concurrent_wait} detik sebelum mencoba kembali ({attempt + 1}/{max_concurrent_retries})..."
                        )
                        # Tunggu sambil cek stop signal
                        for _ in range(concurrent_wait):
                            if self._stopped():
                                return False
                            time.sleep(1)
                        # Retry: type prompt lagi karena halaman mungkin berubah
                        self.type_prompt(prompt_text)
                    else:
                        self.log("  ✗ Gagal: Limit antrean terlampaui")
                        return False

            return False

        except Exception as e:
            self.log(f"  ✗ Gagal generate video: {e}")
            return False



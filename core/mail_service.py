import json
import random
import re
import string
import time
from typing import Callable, Optional

import requests
from config import EMAIL_POLL_INTERVAL, EMAIL_WAIT_TIMEOUT


class TempTFMailService:
    """
    Next-Gen Rotating Mail Engine via Temp-Mail.io REST API:
    - Rotates obscure TLDs & fresh domains (e.g. @ruutukf.com, @gmeenramy.com, @ooynib.com, @olipii.com)
    - Bypass global disposable blocklists (unlisted & rotated regularly)
    - Instant OTP extraction from subject and body
    """

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self.email_address = None
        self.token = None
        self.cached_domains = [
            "ruutukf.com",
            "gmeenramy.com",
            "olipii.com",
            "ooynib.com",
            "lnovic.com",
            "ozsaip.com",
            "yzcalo.com",
        ]

    def create_inbox(self) -> str:
        """Create fresh unique temporary mailbox with an obscure non-blacklisted domain."""
        # 1. Update daftar domain terbaru dari API
        try:
            dom_res = self.session.get("https://api.internal.temp-mail.io/api/v3/domains", timeout=6)
            if dom_res.status_code == 200:
                domains_data = dom_res.json().get("domains", [])
                names = [d["name"] for d in domains_data if "name" in d]
                if names:
                    self.cached_domains = names
        except Exception:
            pass

        # Pilih domain secara acak (hindari yang paling atas / sering dipakai)
        selected_domain = random.choice(self.cached_domains)
        # Buat nama user yang menyerupai nama natural (bukan bot string acak)
        first_names = ["alex", "jordan", "david", "kevin", "brian", "marcus", "ryan", "steven", "daniel", "arthur"]
        rand_name = random.choice(first_names) + "".join(random.choices(string.digits, k=5))

        payload = {
            "name": rand_name,
            "domain": selected_domain,
        }

        try:
            res = self.session.post("https://api.internal.temp-mail.io/api/v3/email/new", json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                self.email_address = data.get("email")
                self.token = data.get("token")
                return self.email_address
        except Exception as e:
            pass

        # Fallback random generate jika custom nama gagal
        try:
            res = self.session.post(
                "https://api.internal.temp-mail.io/api/v3/email/new",
                json={"min_name_length": 8, "max_name_length": 10},
                timeout=8,
            )
            if res.status_code == 200:
                data = res.json()
                self.email_address = data.get("email")
                self.token = data.get("token")
                return self.email_address
        except Exception:
            pass

        raise RuntimeError("Gagal mendapatkan email dari engine Temp-Mail.io.")

    def poll_for_otp(
        self,
        email: str,
        timeout: int = EMAIL_WAIT_TIMEOUT,
        stop_check: Optional[Callable[[], bool]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Poll inbox for PixVerse verification OTP."""
        start_time = time.time()
        last_log = 0

        while time.time() - start_time < timeout:
            if stop_check and stop_check():
                raise InterruptedError("Proses dihentikan oleh pengguna.")

            elapsed = int(time.time() - start_time)
            if log_callback and (time.time() - last_log >= 4):
                last_log = time.time()
                log_callback(f"Menunggu kode OTP masuk ke {email} ({elapsed}s/{timeout}s)...")

            try:
                res = self.session.get(
                    f"https://api.internal.temp-mail.io/api/v3/email/{email}/messages",
                    timeout=7,
                )
                if res.status_code == 200:
                    messages = res.json()
                    if isinstance(messages, list) and messages:
                        for msg in messages:
                            subject = msg.get("subject", "")
                            body_text = msg.get("body_text", "")
                            body_html = msg.get("body_html", "")
                            combined = f"{subject} {body_text} {body_html}"
                            otp = self._extract_otp_from_text(combined)
                            if otp:
                                return otp
            except Exception:
                pass

            time.sleep(1.8)

        raise TimeoutError(f"Waktu habis ({timeout}s) menunggu kode OTP dari PixVerse.")

    @staticmethod
    def _extract_otp_from_text(text: str) -> Optional[str]:
        if not text:
            return None
        # 1. Konteks kata sandi / verifikasi / code
        ctx = re.search(r"(?:code|kode|verification|verify)[^\d]{1,20}(\d{6})", text, re.IGNORECASE)
        if ctx:
            return ctx.group(1)
        # 2. Standalone 6 digit angka
        m = re.findall(r"\b(\d{6})\b", text)
        return m[0] if m else None

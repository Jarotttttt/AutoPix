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
    Multi-Provider Resilient Mail Engine:
    1. Primary: Inboxes.com (Rotated pool of 18+ clean, unblocked domains)
    2. Secondary: Mail.tm (Instant API responses)
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
        })
        self.engine = "inboxes.com"
        self.email_address = None
        self.mailtm_token = None

        # Pool domain inboxes.com yang bersih dari filter Cloudflare / PixVerse
        self.inboxes_domains = [
            "givmail.com",
            "replyloop.com",
            "tafmail.com",
            "chapsmail.com",
            "dropjar.com",
            "getairmail.com",
            "fivermail.com",
            "inboxbear.com",
        ]

    def create_inbox(self) -> str:
        """Create fresh unique temporary mailbox using fresh rotated domains."""
        # 1. Coba Inboxes.com (Pool domain alternatif)
        try:
            domain_res = self.session.get("https://inboxes.com/api/v2/domain", timeout=7)
            if domain_res.status_code == 200:
                online_domains = [d.get("qdn") for d in domain_res.json().get("domains", []) if d.get("qdn")]
                if online_domains:
                    self.inboxes_domains = online_domains

            chosen_domain = random.choice(self.inboxes_domains)
            rand_user = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
            self.email_address = f"user_{rand_user}@{chosen_domain}"
            self.engine = "inboxes.com"
            return self.email_address
        except Exception:
            pass

        # 2. Fallback Mail.tm
        try:
            d_res = self.session.get("https://api.mail.tm/domains", timeout=6)
            domain = d_res.json()["hydra:member"][0]["domain"]
            rand_user = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
            address = f"user_{rand_user}@{domain}"
            pwd = "PixVersePass_99!"
            self.session.post("https://api.mail.tm/accounts", json={"address": address, "password": pwd}, timeout=6)
            token = self.session.post("https://api.mail.tm/token", json={"address": address, "password": pwd}, timeout=6).json().get("token")
            if token:
                self.email_address = address
                self.mailtm_token = token
                self.engine = "mail.tm"
                return address
        except Exception:
            pass

        raise RuntimeError("Gagal membuat email disposable dari semua provider.")

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

            # Engine: Inboxes.com
            if self.engine == "inboxes.com":
                try:
                    res = self.session.get(f"https://inboxes.com/api/v2/inbox/{email}", timeout=7)
                    if res.status_code == 200:
                        msgs = res.json().get("msgs", [])
                        for m in msgs:
                            subject = m.get("s", "")
                            otp = self._extract_otp_from_text(subject)
                            if otp:
                                return otp

                            # Ambil detail message body
                            msg_id = m.get("uid") or m.get("id")
                            if msg_id:
                                detail = self.session.get(f"https://inboxes.com/api/v2/message/{msg_id}", timeout=7).json()
                                full_text = f"{detail.get('text', '')} {detail.get('html', '')}"
                                otp = self._extract_otp_from_text(full_text)
                                if otp:
                                    return otp
                except Exception:
                    pass

            # Engine: Mail.tm
            elif self.engine == "mail.tm" and self.mailtm_token:
                try:
                    headers = {"Authorization": f"Bearer {self.mailtm_token}"}
                    m_res = self.session.get("https://api.mail.tm/messages", headers=headers, timeout=6)
                    if m_res.status_code == 200:
                        for item in m_res.json().get("hydra:member", []):
                            otp = self._extract_otp_from_text(f"{item.get('subject', '')} {item.get('intro', '')}")
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

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
    Robust Mail Service with Automatic Failover:
    - Primary: Mail.tm (Dedicated inbox, high rate-limit ceiling, zero Cloudflare blocks)
    - Fallback: temp.tf (EDU/rotations)
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
        self.engine = "mail.tm"
        self.token = None
        self.email_address = None
        self.domain = "uberip.com"

    def create_inbox(self) -> str:
        """Create fresh unique temporary mailbox."""
        # 1. Coba Mail.tm terlebih dahulu (Sangat stabil & tidak kena 429)
        try:
            email, token = self._create_mailtm()
            self.engine = "mail.tm"
            self.token = token
            self.email_address = email
            return email
        except Exception:
            pass

        # 2. Fallback ke temp.tf jika Mail.tm terkendala
        try:
            res = self.session.get("https://temp.tf/api/account?providers=high.edu.pl", timeout=8)
            if res.status_code == 200:
                email = res.json().get("email")
                if email and "@" in email:
                    self.engine = "temp.tf"
                    self.email_address = email.strip().lower()
                    return self.email_address
        except Exception:
            pass

        raise RuntimeError("Gagal membuat email sementara dari semua provider.")

    def _create_mailtm(self) -> tuple:
        """Create a dedicated Mail.tm inbox and acquire JWT Bearer token."""
        # Ambil domain aktif
        try:
            d_res = self.session.get("https://api.mail.tm/domains", timeout=8)
            members = d_res.json().get("hydra:member", [])
            if members:
                self.domain = members[0]["domain"]
        except Exception:
            pass

        rand_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"user_{rand_id}@{self.domain}"
        password = "PixVersePass_99!"

        payload = {"address": address, "password": password}
        reg_res = self.session.post("https://api.mail.tm/accounts", json=payload, timeout=8)
        if reg_res.status_code not in (200, 201):
            raise RuntimeError(f"Gagal create akun mail.tm: {reg_res.text}")

        token_res = self.session.post("https://api.mail.tm/token", json=payload, timeout=8)
        token = token_res.json().get("token")
        if not token:
            raise RuntimeError("Gagal memperoleh token mail.tm")

        return address, token

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

            # Engine: Mail.tm
            if self.engine == "mail.tm" and self.token:
                try:
                    headers = {"Authorization": f"Bearer {self.token}"}
                    m_res = self.session.get("https://api.mail.tm/messages", headers=headers, timeout=6)
                    if m_res.status_code == 200:
                        items = m_res.json().get("hydra:member", [])
                        for item in items:
                            subject = item.get("subject", "")
                            intro = item.get("intro", "")
                            otp = self._extract_otp_from_text(f"{subject} {intro}")
                            if otp:
                                return otp

                            # Ambil detail message lengkap
                            msg_id = item.get("id")
                            if msg_id:
                                detail = self.session.get(
                                    f"https://api.mail.tm/messages/{msg_id}",
                                    headers=headers,
                                    timeout=6,
                                ).json()
                                full_text = f"{detail.get('text', '')} {detail.get('html', '')}"
                                otp = self._extract_otp_from_text(full_text)
                                if otp:
                                    return otp
                except Exception:
                    pass

            # Engine: temp.tf
            elif self.engine == "temp.tf":
                try:
                    payload = {"email": email, "wait": False}
                    res = self.session.post("https://temp.tf/api/check", json=payload, timeout=8)
                    if res.status_code == 200:
                        msgs = res.json().get("data", [])
                        for m in msgs:
                            full_text = f"{m.get('subject', '')} {m.get('snippet', '')} {m.get('text', '')} {m.get('html', '')}"
                            otp = self._extract_otp_from_text(full_text)
                            if otp:
                                return otp
                except Exception:
                    pass

            time.sleep(EMAIL_POLL_INTERVAL)

        raise TimeoutError(f"Waktu habis ({timeout}s) menunggu kode OTP dari PixVerse.")

    @staticmethod
    def _extract_otp_from_text(text: str) -> Optional[str]:
        if not text:
            return None
        # 1. Konteks code / verify
        ctx = re.search(r"(?:code|kode|verification|verify)[^\d]{1,20}(\d{6})", text, re.IGNORECASE)
        if ctx:
            return ctx.group(1)
        # 2. Standalone 6 digit
        m = re.findall(r"\b(\d{6})\b", text)
        return m[0] if m else None

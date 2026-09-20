import json
import random
import re
import string
import time
from typing import Callable, Optional

import requests
from config import EMAIL_POLL_INTERVAL, EMAIL_WAIT_TIMEOUT, TEMP_TF_ACCOUNT_API, TEMP_TF_CHECK_API


class TempTFMailService:
    """
    High-speed Disposable Mailbox Client with Dual-Engine Architecture:
    1. Primary Engine: temp.tf (clean EDU/Outlook/Gmail domains)
    2. Fast-Polling Engine: Mail.tm (instant sub-second API responses & dedicated webhooks)
    """

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            "Referer": "https://temp.tf/",
            "Accept": "application/json, text/plain, */*",
        })
        self.active_provider = "temp.tf"
        self._mailtm_token = None
        self._mailtm_domain = "uberip.com"

    def create_inbox(self) -> str:
        """
        Request a fresh email address.
        Tries temp.tf first; if slow/unreachable, falls back to mail.tm.
        """
        # 1. Coba temp.tf API
        urls_to_try = [
            TEMP_TF_ACCOUNT_API,
            f"{TEMP_TF_ACCOUNT_API}?providers=high.edu.pl",
            f"{TEMP_TF_ACCOUNT_API}?providers=outlook.com&plus=1",
        ]

        for url in urls_to_try:
            try:
                res = self.session.get(url, timeout=8)
                if res.status_code == 200:
                    data = res.json()
                    email = data.get("email")
                    if email and isinstance(email, str) and "@" in email:
                        self.active_provider = "temp.tf"
                        return email.strip().lower()
            except Exception:
                continue

        # 2. Fallback ke Mail.tm (Super fast)
        try:
            email, token = self._create_mailtm_inbox()
            self._mailtm_token = token
            self.active_provider = "mail.tm"
            return email
        except Exception as e:
            raise RuntimeError(f"Gagal membuat temporary email dari semua provider: {e}")

    def _create_mailtm_inbox(self) -> tuple:
        """Create fresh inbox on Mail.tm."""
        rand_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        email = f"user_{rand_id}@{self._mailtm_domain}"
        password = "PixPassword!99"

        payload = {"address": email, "password": password}
        res = self.session.post("https://api.mail.tm/accounts", json=payload, timeout=8)
        if res.status_code not in (200, 201):
            # Refresh domain
            dom_res = self.session.get("https://api.mail.tm/domains", timeout=8)
            members = dom_res.json().get("hydra:member", [])
            if members:
                self._mailtm_domain = members[0]["domain"]
                email = f"user_{rand_id}@{self._mailtm_domain}"
                payload["address"] = email
                self.session.post("https://api.mail.tm/accounts", json=payload, timeout=8)

        token_res = self.session.post("https://api.mail.tm/token", json=payload, timeout=8)
        token_data = token_res.json()
        token = token_data.get("token")
        return email, token

    def poll_for_otp(
        self,
        email: str,
        timeout: int = EMAIL_WAIT_TIMEOUT,
        stop_check: Optional[Callable[[], bool]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        High-frequency adaptive polling for OTP verification email.
        Poll interval dynamically scales (fast 1.2s checks initially, then 2.5s).
        """
        start_time = time.time()
        last_log_time = 0

        while time.time() - start_time < timeout:
            if stop_check and stop_check():
                raise InterruptedError("Proses polling OTP dihentikan oleh pengguna.")

            elapsed = int(time.time() - start_time)
            if log_callback and (time.time() - last_log_time >= 4):
                last_log_time = time.time()
                log_callback(f"Menunggu kode OTP masuk ({elapsed}s/{timeout}s)...")

            # Polling temp.tf
            if self.active_provider == "temp.tf":
                try:
                    payload = {"email": email, "wait": False}
                    res = self.session.post(
                        TEMP_TF_CHECK_API,
                        json=payload,
                        timeout=5,
                    )
                    if res.status_code == 200:
                        body = res.json()
                        messages = body.get("data", [])
                        if messages:
                            for msg in messages:
                                otp = self._extract_otp_from_message(msg)
                                if otp:
                                    return otp
                except Exception:
                    pass

            # Polling Mail.tm
            elif self.active_provider == "mail.tm" and self._mailtm_token:
                try:
                    headers = {"Authorization": f"Bearer {self._mailtm_token}"}
                    res = self.session.get("https://api.mail.tm/messages", headers=headers, timeout=5)
                    if res.status_code == 200:
                        members = res.json().get("hydra:member", [])
                        for item in members:
                            subject = item.get("subject", "")
                            intro = item.get("intro", "")
                            otp = self._extract_otp_from_text(f"{subject} {intro}")
                            if otp:
                                return otp
                            # Fetch full message
                            msg_id = item.get("id")
                            if msg_id:
                                detail = self.session.get(f"https://api.mail.tm/messages/{msg_id}", headers=headers, timeout=5).json()
                                otp = self._extract_otp_from_message(detail)
                                if otp:
                                    return otp
                except Exception:
                    pass

            # Adaptive fast sleep: 1.2s untuk 30 detik pertama, lalu 2.5s
            poll_interval = 1.2 if elapsed < 30 else 2.5
            time.sleep(poll_interval)

        raise TimeoutError(f"Waktu habis ({timeout}s) menunggu kode OTP dari PixVerse.")

    @classmethod
    def _extract_otp_from_text(cls, text: str) -> Optional[str]:
        if not text:
            return None
        # Prioritas 1: cocokkan konteks OTP/code/verify
        ctx = re.search(r"(?:code|kode|verification|verify)[^\d]{1,20}(\d{6})", text, re.IGNORECASE)
        if ctx:
            return ctx.group(1)
        # Prioritas 2: angka 6 digit standalone
        m = re.findall(r"\b(\d{6})\b", text)
        return m[0] if m else None

    @classmethod
    def _extract_otp_from_message(cls, msg: dict) -> Optional[str]:
        search_fields = [
            msg.get("subject", ""),
            msg.get("snippet", ""),
            msg.get("intro", ""),
            msg.get("text", ""),
            msg.get("html", ""),
        ]
        for field in search_fields:
            otp = cls._extract_otp_from_text(field)
            if otp:
                return otp
        return None

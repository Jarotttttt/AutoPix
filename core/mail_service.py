import json
import re
import time
from typing import Callable, Optional

import requests
from config import EMAIL_POLL_INTERVAL, EMAIL_WAIT_TIMEOUT, TEMP_TF_ACCOUNT_API, TEMP_TF_CHECK_API


class TempTFMailService:
    """
    Client for temp.tf disposable mailbox.
    Uses realistic domains (e.g., @high.edu.pl, Outlook/Gmail aliases) that pass PixVerse detection.
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

    def create_inbox(self) -> str:
        """
        Request a fresh email address from temp.tf.
        Tries generic endpoint first, then specific edu/outlook provider if needed.
        """
        urls_to_try = [
            f"{TEMP_TF_ACCOUNT_API}",
            f"{TEMP_TF_ACCOUNT_API}?providers=high.edu.pl",
            f"{TEMP_TF_ACCOUNT_API}?providers=outlook.com&plus=1",
        ]

        for url in urls_to_try:
            try:
                res = self.session.get(url, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    email = data.get("email")
                    if email and isinstance(email, str) and "@" in email:
                        return email.strip().lower()
            except Exception:
                continue

        raise RuntimeError("Gagal mendapatkan email dari temp.tf API.")

    def poll_for_otp(
        self,
        email: str,
        timeout: int = EMAIL_WAIT_TIMEOUT,
        stop_check: Optional[Callable[[], bool]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Poll temp.tf check endpoint until verification email arrives, then parse 6-digit OTP.
        """
        start_time = time.time()
        poll_count = 0

        while time.time() - start_time < timeout:
            if stop_check and stop_check():
                raise InterruptedError("Proses polling OTP dihentikan oleh pengguna.")

            poll_count += 1
            if log_callback and poll_count % 3 == 0:
                elapsed = int(time.time() - start_time)
                log_callback(f"Menunggu email OTP PixVerse ({elapsed}s/{timeout}s)...")

            try:
                payload = {"email": email, "wait": False}
                res = self.session.post(
                    TEMP_TF_CHECK_API,
                    json=payload,
                    timeout=10,
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

            time.sleep(EMAIL_POLL_INTERVAL)

        raise TimeoutError(f"Waktu habis ({timeout}s) menunggu kode OTP dari PixVerse.")

    @staticmethod
    def _extract_otp_from_message(msg: dict) -> Optional[str]:
        """Extract 6-digit OTP code from subject, snippet, html, or text fields."""
        search_fields = [
            msg.get("subject", ""),
            msg.get("snippet", ""),
            msg.get("text", ""),
            msg.get("html", ""),
        ]

        # Prioritize matching patterns like 'code: 123456', 'verification code 123456'
        for text in search_fields:
            if not text:
                continue
            context_match = re.search(r"(?:code|kode|verification|verify)[^\d]{1,15}(\d{6})", text, re.IGNORECASE)
            if context_match:
                return context_match.group(1)

        # Fallback to any 6-digit standalone sequence
        for text in search_fields:
            if not text:
                continue
            matches = re.findall(r"\b(\d{6})\b", text)
            if matches:
                return matches[0]

        return None

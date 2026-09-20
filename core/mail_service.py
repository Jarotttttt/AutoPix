import json
import re
import time
from typing import Callable, Optional

import requests
from config import EMAIL_WAIT_TIMEOUT, TEMP_TF_ACCOUNT_API, TEMP_TF_CHECK_API


class TempTFMailService:
    """
    Temporary Gmail Engine via temp.tf.
    Converted from Node.js axios scraper implementation:
    - GET  https://temp.tf/api/account?providers=gmail&dot=1&plus=1
    - POST https://temp.tf/api/check with { email, wait: True } (Long-Polling)
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
            "Referer": "https://temp.tf",
        })

    def create_inbox(self) -> str:
        """
        Request a real temporary Gmail address using dot and plus syntax.
        Matches Node.js snippet: providers=gmail, dot=1, plus=1.
        """
        params = {
            "providers": "gmail",
            "dot": 1,
            "plus": 1,
        }

        try:
            res = self.session.get(TEMP_TF_ACCOUNT_API, params=params, timeout=12)
            if res.status_code == 200:
                data = res.json()
                email = data.get("email")
                if email and isinstance(email, str) and "@" in email:
                    return email.strip()
        except Exception as e:
            pass

        # Fallback to general provider if gmail limit hit
        fallback_res = self.session.get(TEMP_TF_ACCOUNT_API, timeout=10)
        data = fallback_res.json()
        email = data.get("email")
        if email:
            return email.strip()

        raise RuntimeError("Gagal mendapatkan email Gmail dari temp.tf API.")

    def poll_for_otp(
        self,
        email: str,
        timeout: int = EMAIL_WAIT_TIMEOUT,
        stop_check: Optional[Callable[[], bool]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Long-poll temp.tf check API with wait: True for instant OTP arrival.
        Server holds connection open and pushes message the moment it arrives.
        """
        start_time = time.time()
        poll_count = 0

        while time.time() - start_time < timeout:
            if stop_check and stop_check():
                raise InterruptedError("Proses dihentikan oleh pengguna.")

            poll_count += 1
            elapsed = int(time.time() - start_time)
            if log_callback and (poll_count == 1 or poll_count % 2 == 0):
                log_callback(f"Menunggu kode OTP masuk ke {email} ({elapsed}s/{timeout}s)...")

            try:
                # Long-polling wait: True sesuai snippet Node.js
                payload = {
                    "email": email,
                    "wait": True,
                }
                res = self.session.post(
                    TEMP_TF_CHECK_API,
                    json=payload,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                    timeout=20,
                )

                if res.status_code == 200:
                    data = res.json().get("data", [])
                    if data:
                        for msg in data:
                            otp = self._extract_otp_from_message(msg)
                            if otp:
                                return otp
            except requests.exceptions.Timeout:
                # Normal saat long-poll timeout, langsung loop berikutnya
                continue
            except Exception:
                time.sleep(1)

        raise TimeoutError(f"Waktu habis ({timeout}s) menunggu kode OTP dari PixVerse.")

    @classmethod
    def _extract_otp_from_message(cls, msg: dict) -> Optional[str]:
        search_fields = [
            msg.get("subject", ""),
            msg.get("snippet", ""),
            msg.get("text", ""),
            msg.get("html", ""),
        ]

        # Prioritas: Cocokkan kata kunci kode verifikasi
        for text in search_fields:
            if not text:
                continue
            ctx = re.search(r"(?:code|kode|verification|verify)[^\d]{1,20}(\d{6})", text, re.IGNORECASE)
            if ctx:
                return ctx.group(1)

        # Fallback: Cari 6 digit angka
        for text in search_fields:
            if not text:
                continue
            matches = re.findall(r"\b(\d{6})\b", text)
            if matches:
                return matches[0]

        return None

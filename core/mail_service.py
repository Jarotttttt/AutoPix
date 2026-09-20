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
    Dual Engine High-Reliability Mail Service:
    1. Primary Engine: TempMail.plus (Domains: rover.info, fexbox.org, merepost.com, any.pink)
       - Obscure non-mail domain extensions (.info, .org, .pink)
       - Bypass global disposable blocklists
       - Direct, fast JSON API with zero delay
    2. Fallback Engine: Temp-Mail.io (ruutukf.com, olipii.com, etc.)
    """

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
        })
        self.engine = "tempmail_plus"
        self.email_address = None
        self.token = None

        # Domain-domain non-mail yang lolos filter PixVerse
        self.plus_domains = [
            "rover.info",
            "fexbox.org",
            "merepost.com",
            "any.pink",
            "fextemp.com",
        ]

    def create_inbox(self) -> str:
        """Generate fresh inbox with a clean, natural username on an unblocked domain."""
        # 1. Gunakan TempMail.plus dengan domain acak
        try:
            chosen_domain = random.choice(self.plus_domains)
            # Pola nama user natural: nama depan + angka
            first_names = ["alex", "jordan", "david", "kevin", "brian", "marcus", "ryan", "steven", "daniel", "arthur"]
            rand_name = random.choice(first_names) + "".join(random.choices(string.digits, k=5))
            self.email_address = f"{rand_name}@{chosen_domain}"
            self.engine = "tempmail_plus"
            return self.email_address
        except Exception:
            pass

        # 2. Fallback ke Temp-Mail.io jika perlu
        try:
            dom_res = self.session.get("https://api.internal.temp-mail.io/api/v3/domains", timeout=6)
            domain_name = "ruutukf.com"
            if dom_res.status_code == 200:
                domains_data = dom_res.json().get("domains", [])
                if domains_data:
                    domain_name = random.choice(domains_data).get("name", "ruutukf.com")

            rand_user = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
            payload = {"name": rand_user, "domain": domain_name}
            res = self.session.post("https://api.internal.temp-mail.io/api/v3/email/new", json=payload, timeout=6)
            if res.status_code == 200:
                data = res.json()
                self.email_address = data.get("email")
                self.token = data.get("token")
                self.engine = "temp_mail_io"
                return self.email_address
        except Exception:
            pass

        raise RuntimeError("Gagal membuat email sementara.")

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

            # Engine: TempMail.plus
            if self.engine == "tempmail_plus":
                try:
                    url = f"https://tempmail.plus/api/mails?email={email}&limit=5"
                    res = self.session.get(url, timeout=6)
                    if res.status_code == 200:
                        body = res.json()
                        mail_list = body.get("mail_list", [])
                        for item in mail_list:
                            subject = item.get("subject", "")
                            otp = self._extract_otp_from_text(subject)
                            if otp:
                                return otp

                            mail_id = item.get("mail_id")
                            if mail_id:
                                detail_url = f"https://tempmail.plus/api/mails/{mail_id}?email={email}"
                                detail_res = self.session.get(detail_url, timeout=6).json()
                                full_content = f"{detail_res.get('text', '')} {detail_res.get('html', '')}"
                                otp = self._extract_otp_from_text(full_content)
                                if otp:
                                    return otp
                except Exception:
                    pass

            # Engine: Temp-Mail.io
            elif self.engine == "temp_mail_io":
                try:
                    res = self.session.get(
                        f"https://api.internal.temp-mail.io/api/v3/email/{email}/messages",
                        timeout=6,
                    )
                    if res.status_code == 200:
                        messages = res.json()
                        if isinstance(messages, list) and messages:
                            for msg in messages:
                                full_text = f"{msg.get('subject', '')} {msg.get('body_text', '')} {msg.get('body_html', '')}"
                                otp = self._extract_otp_from_text(full_text)
                                if otp:
                                    return otp
                except Exception:
                    pass

            time.sleep(1.5)

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

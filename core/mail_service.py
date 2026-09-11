import random
import re
import string
import time
from typing import Callable, Optional

import requests
from config import EMAIL_WAIT_TIMEOUT, TEMP_MAIL_API_BASE


def is_connected() -> bool:
    """Check whether internet connection is reachable."""
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.RequestException:
        return False


def get_temp_email(session: requests.Session) -> str:
    """Create a new temporary email via temp-mail.ai API."""
    resp = session.post(f"{TEMP_MAIL_API_BASE}/random", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise Exception("Gagal mendapatkan email sementara dari temp-mail.ai")
    return data.get("email")


def check_inbox(
    session: requests.Session,
    email: str,
    wait: int = EMAIL_WAIT_TIMEOUT,
    stop_check: Optional[Callable[[], bool]] = None,
) -> Optional[dict]:
    """Poll temp-mail.ai inbox until verification message arrives or timeout."""
    safe_email = requests.utils.quote(email)
    url = f"{TEMP_MAIL_API_BASE}/{safe_email}/messages"

    for _ in range(wait):
        if stop_check and stop_check():
            return None

        time.sleep(2)
        try:
            resp = session.get(url, timeout=10)
            data = resp.json()
            if data.get("success") and data.get("messages"):
                msg = data.get("messages")[0]
                # If message body is truncated/empty, fetch message detail
                if not msg.get("text") and not msg.get("html"):
                    msg_id = msg.get("id")
                    detail_url = f"{TEMP_MAIL_API_BASE}/{safe_email}/message/{msg_id}"
                    detail_resp = session.get(detail_url, timeout=10)
                    detail_data = detail_resp.json()
                    if detail_data.get("success"):
                        return detail_data.get("message")
                return msg
        except requests.RequestException:
            pass

    return None


def extract_otp(message: Optional[dict]) -> Optional[str]:
    """Extract 6-digit OTP code from email subject or body."""
    if not message:
        return None

    candidates = [
        message.get("text", ""),
        message.get("html", ""),
        message.get("subject", ""),
    ]
    for text in candidates:
        if text:
            matches = re.findall(r"\b(\d{6})\b", text)
            if matches:
                return matches[0]
    return None


def random_username(length: int = 10) -> str:
    """Generate a random username string."""
    chars = string.ascii_lowercase + string.digits
    return "user_" + "".join(random.choices(chars, k=length))


def random_password(length: int = 12) -> str:
    """Generate strong random password containing uppercase, lowercase, numbers, and symbols."""
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + "!@#$%^&*"
    pwd = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice("!@#$%^&*"),
    ]
    pwd += random.choices(chars, k=length - 4)
    random.shuffle(pwd)
    return "".join(pwd)

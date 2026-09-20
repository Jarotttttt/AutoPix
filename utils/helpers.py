import random
import string
from typing import List


def is_connected() -> bool:
    """Check whether internet connection is reachable."""
    try:
        import requests
        requests.get("https://www.google.com", timeout=5)
        return True
    except Exception:
        return False


def random_username(prefix: str = "pix_") -> str:
    """Generate clean random username string."""
    chars = string.ascii_lowercase + string.digits
    return prefix + "".join(random.choices(chars, k=8))


def random_password(length: int = 12) -> str:
    """
    Generate strong random password meeting PixVerse criteria:
    Uppercase, lowercase, numbers, and allowed special symbols.
    """
    upper = random.choice(string.ascii_uppercase)
    lower = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    spec = random.choice("!@#$%^&*")
    all_chars = string.ascii_letters + string.digits + "!@#$%^&*"
    remainder = random.choices(all_chars, k=max(length - 4, 4))
    pwd_list = [upper, lower, digit, spec] + remainder
    random.shuffle(pwd_list)
    return "".join(pwd_list)


def parse_prompts(raw_text: str) -> List[str]:
    """Parse multiline raw text into a list of non-empty prompts."""
    if not raw_text or not raw_text.strip():
        return []

    lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
    return lines

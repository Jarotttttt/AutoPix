import os
import sys

# ── App Metadata ─────────────────────────────────────────────────────────────
APP_NAME = "AutoPix"
APP_VERSION = "v4.0"
APP_ID = "autopix.pixverse.flow.4.0"

# ── Service Endpoints ────────────────────────────────────────────────────────
# Temp mail provider: temp.tf (clean rotated domains / EDU / Outlook / Gmail)
TEMP_TF_BASE_URL = "https://temp.tf"
TEMP_TF_ACCOUNT_API = f"{TEMP_TF_BASE_URL}/api/account"
TEMP_TF_CHECK_API = f"{TEMP_TF_BASE_URL}/api/check"

# PixVerse Endpoints
PIXVERSE_HOME_URL = "https://app.pixverse.ai/"
PIXVERSE_REG_URL = "https://app.pixverse.ai/register"
PIXVERSE_LOGIN_URL = "https://app.pixverse.ai/login"
PIXVERSE_VIDEO_URL = "https://app.pixverse.ai/creation/video"

# ── Automation Settings & Delays ─────────────────────────────────────────────
EMAIL_WAIT_TIMEOUT = 120  # seconds to wait for verification code
EMAIL_POLL_INTERVAL = 3   # seconds between inbox polling
REGISTRATION_TIMEOUT = 25 # seconds waiting for form elements
MAX_VIDEOS_PER_ACCOUNT = 3 # Free quota per fresh PixVerse account
CONCURRENT_LIMIT_MAX_RETRIES = 3
CONCURRENT_LIMIT_WAIT_SECONDS = 40

# ── Paths ────────────────────────────────────────────────────────────────────
DEFAULT_DOWNLOAD_FOLDER = "downloads"


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

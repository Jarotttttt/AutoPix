import os
import sys

# ── App Metadata ─────────────────────────────────────────────────────────────
APP_NAME = "AutoPix"
APP_VERSION = "v3.0"
APP_ID = "autopixverse.app.1.0"

# ── Service Endpoints ────────────────────────────────────────────────────────
TEMP_MAIL_API_BASE = "https://temp-mail.ai/api/mailbox"
PIXVERSE_REG_URL = "https://app.pixverse.ai/register"
PIXVERSE_VIDEO_URL = "https://app.pixverse.ai/creation/video"
PIXVERSE_HOME_URL = "https://app.pixverse.ai/"

# ── Automation Settings & Delays ─────────────────────────────────────────────
EMAIL_WAIT_TIMEOUT = 90
BROWSER_LAUNCH_STAGGER_DELAY = 2.5
CONCURRENT_LIMIT_MAX_RETRIES = 3
CONCURRENT_LIMIT_WAIT_SECONDS = 45

# ── Default Paths ────────────────────────────────────────────────────────────
DEFAULT_DOWNLOAD_FOLDER = "downloads"


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

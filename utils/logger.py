from datetime import datetime
from typing import Callable, Optional


class AppLogger:
    """Thread-safe logger dispatcher for GUI log terminal and console."""

    def __init__(self, callback: Optional[Callable[[str, str], None]] = None):
        self._callback = callback

    def set_callback(self, callback: Callable[[str, str], None]):
        self._callback = callback

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {message}"
        print(formatted)
        if self._callback:
            try:
                self._callback(formatted, level)
            except Exception:
                pass

    def info(self, msg: str):
        self.log(msg, "INFO")

    def success(self, msg: str):
        self.log(msg, "SUCCESS")

    def warn(self, msg: str):
        self.log(msg, "WARN")

    def error(self, msg: str):
        self.log(msg, "ERROR")

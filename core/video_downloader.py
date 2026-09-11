from datetime import datetime
import os
import re
import time
from typing import Callable, List, Optional, Tuple

import requests
from config import PIXVERSE_HOME_URL
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class PixVerseVideoDownloader:
    """Extracts and downloads rendered videos from active PixVerse accounts."""

    def __init__(
        self,
        log_callback: Optional[Callable[[str], None]] = None,
        stop_check: Optional[Callable[[], bool]] = None,
    ):
        self.log = log_callback or print
        self.stop_check = stop_check

    def _stopped(self) -> bool:
        return bool(self.stop_check and self.stop_check())

    def _transfer_cookies(self, driver) -> requests.Session:
        """Transfer active session cookies from Selenium WebDriver to requests.Session."""
        session = requests.Session()
        for cookie in driver.get_cookies():
            session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain", ""),
                path=cookie.get("path", "/"),
            )

        user_agent = driver.execute_script("return navigator.userAgent;")
        session.headers.update(
            {
                "User-Agent": user_agent,
                "Referer": PIXVERSE_HOME_URL,
            }
        )
        return session

    def _find_video_page_links(self, driver) -> List[str]:
        """Find video detail links (/video/{id}) from creation dashboard."""
        video_links = []
        seen_ids = set()

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-media-id]"))
            )
        except Exception:
            self.log("  ⚠️ Timeout menunggu element video muncul di dashboard.")

        time.sleep(0.5)

        items = driver.find_elements(By.CSS_SELECTOR, "[data-media-id]")
        for item in items:
            try:
                media_id = item.get_attribute("data-media-id")
                if media_id and media_id.isdigit() and media_id not in seen_ids:
                    seen_ids.add(media_id)
                    video_links.append(f"https://app.pixverse.ai/video/{media_id}")
            except Exception:
                continue

        # Fallback via JavaScript execution
        try:
            js_ids = driver.execute_script(
                """
                var ids = [];
                document.querySelectorAll('[data-media-id]').forEach(function(el) {
                    var id = el.getAttribute('data-media-id');
                    if (id && /^\\d+$/.test(id)) {
                        ids.push(id);
                    }
                });
                return ids;
            """
            )
            for media_id in js_ids:
                if media_id not in seen_ids:
                    seen_ids.add(media_id)
                    video_links.append(f"https://app.pixverse.ai/video/{media_id}")
        except Exception:
            pass

        return video_links

    def _get_video_src_from_page(self, driver) -> Optional[str]:
        """Extract media MP4 download URL from /video/{id} page."""
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "video[src]"))
            )
        except Exception:
            return None

        time.sleep(0.5)

        for vid in driver.find_elements(By.CSS_SELECTOR, "video[src]"):
            try:
                src = vid.get_attribute("src")
                if src and src.startswith("http") and "media.pixverse.ai" in src:
                    return src
            except Exception:
                continue

        for src_el in driver.find_elements(By.CSS_SELECTOR, "video source[src]"):
            try:
                src = src_el.get_attribute("src")
                if src and src.startswith("http"):
                    return src
            except Exception:
                continue

        for vid in driver.find_elements(By.CSS_SELECTOR, "video[src]"):
            try:
                src = vid.get_attribute("src")
                if src and src.startswith("http"):
                    return src
            except Exception:
                continue

        return None

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        return re.sub(r'[<>:"/\\|?*]', "_", name)

    def _download_file(self, session: requests.Session, url: str, filepath: str) -> bool:
        """Download file with streaming chunks and verify integrity."""
        try:
            resp = session.get(url, stream=True, timeout=120)
            resp.raise_for_status()

            total_size = int(resp.headers.get("content-length", 0))
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if self._stopped():
                        return False
                    if chunk:
                        f.write(chunk)

            if total_size > 0:
                size_mb = total_size / (1024 * 1024)
                self.log(f"  ✓ Berhasil: {os.path.basename(filepath)} ({size_mb:.1f} MB)")
            else:
                self.log(f"  ✓ Berhasil: {os.path.basename(filepath)}")
            return True

        except Exception as e:
            self.log(f"  ✗ Gagal download {os.path.basename(filepath)}: {str(e)[:80]}")
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
            return False

    def download_videos_for_account(self, account: dict, download_folder: str) -> Tuple[int, int]:
        """Download all rendered videos belonging to a single account."""
        index = account["index"]
        email = account["email"]
        driver = account["driver"]

        email_prefix = self._sanitize_filename(email.split("@")[0])
        timestamp = datetime.now().strftime("%H%M%S")

        self.log(f"[Akun {index}] Mencari video...")

        try:
            current_url = driver.current_url.lower()
            if "login" in current_url or "register" in current_url:
                self.log(f"[Akun {index}] Session expired, akun tidak login.")
                return 0, 0

            if "app.pixverse.ai/creation/video" not in current_url:
                driver.execute_script("window.location.href = 'https://app.pixverse.ai/creation/video'")
                time.sleep(1)

            if self._stopped():
                return 0, 0

            video_page_links = self._find_video_page_links(driver)
            if not video_page_links:
                self.log(f"[Akun {index}] Tidak ada video ditemukan.")
                return 0, 0

            self.log(f"[Akun {index}] Ditemukan {len(video_page_links)} video. Mulai download...")
            session = self._transfer_cookies(driver)

            success = 0
            fail = 0

            for vid_num, video_page_url in enumerate(video_page_links, start=1):
                if self._stopped():
                    break

                driver.execute_script(f"window.location.href = '{video_page_url}'")
                time.sleep(0.5)

                video_src = self._get_video_src_from_page(driver)
                if not video_src:
                    self.log(f"  ✗ Link video {vid_num} tidak ditemukan")
                    fail += 1
                    continue

                filename = f"akun{index}_{email_prefix}_video{vid_num}_{timestamp}.mp4"
                filepath = os.path.join(download_folder, filename)

                if os.path.exists(filepath):
                    self.log(f"  ⏭ Skip (sudah ada): {filename}")
                    success += 1
                    continue

                if self._download_file(session, video_src, filepath):
                    success += 1
                else:
                    fail += 1

            return success, fail

        except Exception as e:
            self.log(f"[Akun {index}] Error: {str(e)[:120]}")
            return 0, 0

    def download_all(self, accounts: list, download_folder: str) -> Tuple[int, int]:
        """Download videos across all accounts into download_folder."""
        if not accounts:
            self.log("Tidak ada akun yang tersedia untuk di-download videonya.")
            return 0, 0

        os.makedirs(download_folder, exist_ok=True)
        self.log(f"Memulai download video dari {len(accounts)} akun...")

        total_success = 0
        total_fail = 0

        for account in accounts:
            if self._stopped():
                self.log("Download dihentikan oleh user.")
                break

            s, f = self.download_videos_for_account(account, download_folder)
            total_success += s
            total_fail += f

        self.log(f"Download selesai! Berhasil: {total_success}, Gagal: {total_fail}")
        return total_success, total_fail

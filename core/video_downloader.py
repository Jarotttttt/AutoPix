import os
import re
import time
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime

PIXVERSE_HOME_URL = "https://app.pixverse.ai/"


class PixVerseVideoDownloader:
    """Downloads all generated videos from PixVerse accounts."""

    def __init__(self, log_callback=None, stop_check=None):
        self.log = log_callback or print
        self.stop_check = stop_check

    def _stopped(self) -> bool:
        return bool(self.stop_check and self.stop_check())

    def _transfer_cookies(self, driver):
        """Transfer cookies from Selenium WebDriver to a requests.Session."""
        session = requests.Session()
        for cookie in driver.get_cookies():
            session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain", ""),
                path=cookie.get("path", "/"),
            )
        # Copy common headers from the browser
        user_agent = driver.execute_script("return navigator.userAgent;")
        session.headers.update({
            "User-Agent": user_agent,
            "Referer": PIXVERSE_HOME_URL,
        })
        return session

    def _find_video_page_links(self, driver):
        """Find all /video/{id} links from the current page (dashboard)."""
        video_links = []
        seen_ids = set()

        # Wait for media items to appear on the page
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-media-id]"))
            )
        except Exception:
            self.log("  ⚠️ Timeout menunggu element video muncul di dashboard.")

        time.sleep(0.5)

        # Find elements with data-media-id
        items = driver.find_elements(By.CSS_SELECTOR, "[data-media-id]")
        for item in items:
            try:
                media_id = item.get_attribute("data-media-id")
                # Ensure it's a numeric ID
                if media_id and media_id.isdigit() and media_id not in seen_ids:
                    seen_ids.add(media_id)
                    video_links.append(f"https://app.pixverse.ai/video/{media_id}")
            except Exception:
                continue

        # Also try via JavaScript fallback
        try:
            js_ids = driver.execute_script("""
                var ids = [];
                document.querySelectorAll('[data-media-id]').forEach(function(el) {
                    var id = el.getAttribute('data-media-id');
                    if (id && /^\\d+$/.test(id)) {
                        ids.push(id);
                    }
                });
                return ids;
            """)
            for media_id in js_ids:
                if media_id not in seen_ids:
                    seen_ids.add(media_id)
                    video_links.append(f"https://app.pixverse.ai/video/{media_id}")
        except Exception:
            pass

        return video_links

    def _get_video_src_from_page(self, driver):
        """Extract the video src URL from a /video/{id} page."""
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "video[src]"))
            )
        except Exception:
            return None

        time.sleep(0.5)

        # Get the video src
        video_elements = driver.find_elements(By.CSS_SELECTOR, "video[src]")
        for vid in video_elements:
            try:
                src = vid.get_attribute("src")
                if src and src.startswith("http") and "media.pixverse.ai" in src:
                    return src
            except Exception:
                continue

        # Fallback: check <source> elements
        source_elements = driver.find_elements(By.CSS_SELECTOR, "video source[src]")
        for src_el in source_elements:
            try:
                src = src_el.get_attribute("src")
                if src and src.startswith("http"):
                    return src
            except Exception:
                continue

        # Last fallback: any video with src
        for vid in video_elements:
            try:
                src = vid.get_attribute("src")
                if src and src.startswith("http"):
                    return src
            except Exception:
                continue

        return None

    def _sanitize_filename(self, name):
        """Remove invalid characters from filename."""
        return re.sub(r'[<>:"/\\|?*]', '_', name)

    def _download_file(self, session, url, filepath):
        """Download a single file with streaming."""
        try:
            resp = session.get(url, stream=True, timeout=120)
            resp.raise_for_status()

            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if self._stopped():
                        return False
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

            if total_size > 0:
                size_mb = total_size / (1024 * 1024)
                self.log(f"  ✓ Berhasil: {os.path.basename(filepath)} ({size_mb:.1f} MB)")
            else:
                self.log(f"  ✓ Berhasil: {os.path.basename(filepath)}")
            return True

        except Exception as e:
            self.log(f"  ✗ Gagal download {os.path.basename(filepath)}: {str(e)[:80]}")
            # Clean up partial file
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
            return False

    def download_videos_for_account(self, account, download_folder):
        """
        Download all videos for a single account.
        
        Steps:
        1. Go to dashboard to find all /video/{id} links
        2. Navigate to each video page
        3. Extract download URL and request download
        """
        index = account["index"]
        email = account["email"]
        driver = account["driver"]

        # Create safe email prefix for filename
        email_prefix = self._sanitize_filename(email.split("@")[0])
        timestamp = datetime.now().strftime("%H%M%S")

        self.log(f"[Akun {index}] Mencari video...")

        try:
            # Step 1: Go to dashboard to find video links
            current_url = driver.current_url.lower()
            if "login" in current_url or "register" in current_url:
                self.log(f"[Akun {index}] Session expired, akun tidak login lagi.")
                return 0, 0

            # Navigate to creation dashboard if not already there
            if "app.pixverse.ai/creation/video" not in current_url:
                driver.execute_script("window.location.href = 'https://app.pixverse.ai/creation/video'")
                time.sleep(1)

            if self._stopped():
                return 0, 0

            # Step 2: Find all /video/{id} links on the dashboard
            video_page_links = self._find_video_page_links(driver)

            if not video_page_links:
                self.log(f"[Akun {index}] Tidak ada video ditemukan.")
                return 0, 0

            self.log(f"[Akun {index}] Ditemukan {len(video_page_links)} video. Mulai download...")

            # Transfer cookies for download
            session = self._transfer_cookies(driver)

            success = 0
            fail = 0

            # Step 3: Visit each video page and download
            for vid_num, video_page_url in enumerate(video_page_links, start=1):
                if self._stopped():
                    break

                # Extract video ID for logging
                vid_id_match = re.search(r'/video/(\d+)', video_page_url)
                vid_id = vid_id_match.group(1) if vid_id_match else str(vid_num)

                # Navigate to the video page
                driver.execute_script(f"window.location.href = '{video_page_url}'")
                time.sleep(0.5)

                # Extract the video src URL from the page
                video_src = self._get_video_src_from_page(driver)

                if not video_src:
                    self.log(f"  ✗ Link video {vid_num} tidak ditemukan")
                    fail += 1
                    continue

                filename = f"akun{index}_{email_prefix}_video{vid_num}_{timestamp}.mp4"
                filepath = os.path.join(download_folder, filename)

                # Skip if already exists
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

    def download_all(self, accounts, download_folder):
        """
        Download videos from all accounts.
        
        accounts: list of dict {index, email, driver}
        download_folder: path to save videos
        
        Returns: (total_success, total_fail)
        """
        if not accounts:
            self.log("Tidak ada akun yang berhasil untuk di-download videonya.")
            return 0, 0

        # Ensure download folder exists
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

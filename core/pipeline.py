import math
import re
import time
from typing import Callable, List, Optional

from core.account_creator import PixVerseAccountCreator
from core.mail_service import random_password
from core.video_downloader import PixVerseVideoDownloader
from core.video_generator import PixVerseVideoGenerator


def parse_prompts(raw_text: str) -> List[str]:
    """Parse multiline raw text into a list of cleaned prompts."""
    if not raw_text or not raw_text.strip():
        return []

    # First attempt splitting by empty lines
    chunks = [p.strip() for p in re.split(r"\n\s*\n", raw_text.strip()) if p.strip()]

    # If user just separated by single newlines
    if len(chunks) == 1 and "\n" in chunks[0]:
        lines = [line.strip() for line in raw_text.strip().split("\n") if line.strip()]
        if len(lines) > 1:
            chunks = lines

    return chunks


def calculate_batches(prompts: List[str], max_per_account: int = 3) -> List[dict]:
    """
    Split prompts into batches of up to max_per_account (default 3 videos per free account).
    Returns list of dicts: [{'account_index': 1, 'prompts': [...]}, ...]
    """
    if not prompts:
        return []

    total_accounts = math.ceil(len(prompts) / max_per_account)
    batches = []
    for i in range(total_accounts):
        chunk = prompts[i * max_per_account : (i + 1) * max_per_account]
        batches.append({
            "account_index": i + 1,
            "prompts": chunk,
        })
    return batches


class AccountPipelineWorker:
    """Executes full automated lifecycle for a single account: Signup -> Generate -> Download."""

    def __init__(
        self,
        account_index: int,
        prompts: List[str],
        download_folder: str,
        log_callback: Callable[[str], None],
        stop_check: Callable[[], bool],
        driver_tracker_callback: Optional[Callable] = None,
        on_account_created: Optional[Callable[[dict], None]] = None,
        on_video_generated: Optional[Callable[[], None]] = None,
        on_video_downloaded: Optional[Callable[[], None]] = None,
        run_in_background: bool = False,
    ):
        self.index = account_index
        self.prompts = prompts
        self.download_folder = download_folder
        self.log = log_callback
        self.stop_check = stop_check
        self.driver_tracker = driver_tracker_callback
        self.on_account_created = on_account_created
        self.on_video_generated = on_video_generated
        self.on_video_downloaded = on_video_downloaded
        self.run_in_background = run_in_background

    def _is_stopped(self) -> bool:
        return bool(self.stop_check and self.stop_check())

    def run(self) -> bool:
        """Execute the full sequence for this account."""
        if self._is_stopped():
            return False

        # 1. BUAT AKUN
        password = random_password(12)
        self.log(f"[Akun {self.index}] Memulai pendaftaran otomatis...")

        creator = PixVerseAccountCreator(
            log_callback=self.log,
            stop_check=self.stop_check,
            driver_opened_callback=self.driver_tracker,
            run_in_background=self.run_in_background,
        )

        ok, email, driver = creator.create_account(self.index, password)
        if not ok or not driver:
            self.log(f"[Akun {self.index}] Gagal membuat akun. Batch untuk akun ini dilewati.")
            return False

        account_info = {
            "index": self.index,
            "email": email,
            "driver": driver,
        }
        if self.on_account_created:
            self.on_account_created(account_info)

        self.log(f"[Akun {self.index}] Akun siap! Memproses {len(self.prompts)} prompt video...")

        # 2. GENERATE SETIAP PROMPT (MAKS 3)
        generator = PixVerseVideoGenerator(
            driver,
            log_callback=self.log,
            stop_check=self.stop_check,
        )

        videos_submitted = 0
        for vid_idx, prompt in enumerate(self.prompts, start=1):
            if self._is_stopped():
                break

            preview = prompt[:45] + ("..." if len(prompt) > 45 else "")
            self.log(f"[Akun {self.index}] Video {vid_idx}/{len(self.prompts)} -> {preview}")

            gen_ok = generator.generate_video(prompt_text=prompt)
            if gen_ok:
                videos_submitted += 1
                self.log(f"[Akun {self.index}] Video {vid_idx} sukses dikirim ke antrean render.")
                if self.on_video_generated:
                    self.on_video_generated()
            else:
                self.log(f"[Akun {self.index}] Video {vid_idx} gagal dikirim.")

            if vid_idx < len(self.prompts) and not self._is_stopped():
                time.sleep(5)

        if self._is_stopped() or videos_submitted == 0:
            return False

        # 3. TUNGGU DAN DOWNLOAD HASIL
        self.log(f"[Akun {self.index}] Menunggu proses render video selesai (±30 detik)...")
        for _ in range(30):
            if self._is_stopped():
                return False
            time.sleep(1)

        self.log(f"[Akun {self.index}] Mengunduh hasil video ke folder...")
        downloader = PixVerseVideoDownloader(
            log_callback=self.log,
            stop_check=self.stop_check,
        )

        success, fail = downloader.download_videos_for_account(account_info, self.download_folder)
        self.log(f"[Akun {self.index}] Unduhan tuntas: {success} berhasil, {fail} gagal.")

        if self.on_video_downloaded and success > 0:
            for _ in range(success):
                self.on_video_downloaded()

        return True

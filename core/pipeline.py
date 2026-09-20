import math
import time
from typing import Callable, List, Optional

from core.account_creator import AccountCreatorService
from core.video_downloader import PixVerseVideoDownloader
from core.video_generator import PixVerseVideoGenerator
from utils.helpers import parse_prompts


def calculate_batches(prompts: List[str], max_per_account: int = 3) -> List[dict]:
    """
    Split prompt list into batches where each batch maps to 1 fresh PixVerse account.
    Returns: [{'account_index': 1, 'prompts': [...]}, ...]
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
    """
    Executes full automated lifecycle per batch/account:
    1. Sign Up PixVerse with Temp.tf
    2. Submit Video Prompts (up to 3)
    3. Monitor & Download completed MP4 renders
    """

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

    def _is_stopped(self) -> bool:
        return bool(self.stop_check and self.stop_check())

    def run(self) -> bool:
        """Runs the whole flow for this account."""
        if self._is_stopped():
            return False

        # 1. BUAT AKUN VIA TEMP.TF
        creator = AccountCreatorService(
            log_callback=self.log,
            stop_check=self.stop_check,
            driver_tracker=self.driver_tracker,
        )

        ok, email, driver = creator.create_account(self.index)
        if not ok or not driver:
            self.log(f"[Akun #{self.index}] Gagal registrasi akun. Batch ini dilewati.")
            return False

        account_info = {
            "index": self.index,
            "email": email,
            "driver": driver,
        }
        if self.on_account_created:
            self.on_account_created(account_info)

        self.log(f"[Akun #{self.index}] Memproses {len(self.prompts)} prompt video...")

        # 2. GENERATE VIDEO
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
            self.log(f"[Akun #{self.index}] Video {vid_idx}/{len(self.prompts)} -> {preview}")

            gen_ok = generator.generate_video(prompt_text=prompt)
            if gen_ok:
                videos_submitted += 1
                self.log(f"[Akun #{self.index}] Video {vid_idx} masuk antrean render.")
                if self.on_video_generated:
                    self.on_video_generated()
            else:
                self.log(f"[Akun #{self.index}] Video {vid_idx} gagal submit.")

            if vid_idx < len(self.prompts) and not self._is_stopped():
                time.sleep(5)

        if self._is_stopped() or videos_submitted == 0:
            return False

        # 3. POLLING RENDER & DOWNLOAD
        self.log(f"[Akun #{self.index}] Menunggu proses render video di server PixVerse (±30-60 detik)...")
        for _ in range(35):
            if self._is_stopped():
                return False
            time.sleep(1)

        self.log(f"[Akun #{self.index}] Mengunduh hasil video...")
        downloader = PixVerseVideoDownloader(
            log_callback=self.log,
            stop_check=self.stop_check,
        )

        success, fail = downloader.download_videos_for_account(account_info, self.download_folder)
        self.log(f"[Akun #{self.index}] Hasil unduhan: {success} berhasil, {fail} gagal.")

        if self.on_video_downloaded and success > 0:
            for _ in range(success):
                self.on_video_downloaded()

        return True

import ctypes
import os
import threading
from tkinter import messagebox
from typing import List

import customtkinter as ctk

from config import (
    APP_ID,
    APP_NAME,
    APP_VERSION,
    DEFAULT_DOWNLOAD_FOLDER,
    MAX_VIDEOS_PER_ACCOUNT,
    resource_path,
)
from core import AccountPipelineWorker, calculate_batches
from ui import AppUI
from utils import AppLogger, is_connected

# Set explicit Windows Taskbar Application Model ID
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
except Exception:
    pass


class AutoPixApp:
    """Master Application Controller for AutoPix AMOLED Glass Edition."""

    def __init__(self):
        self.window = ctk.CTk()

        # Set App Icon if exists
        icon_file = resource_path("ai.ico")
        if os.path.exists(icon_file):
            try:
                self.window.iconbitmap(icon_file)
            except Exception:
                pass

        # Execution State
        self.default_folder = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            DEFAULT_DOWNLOAD_FOLDER,
        )
        os.makedirs(self.default_folder, exist_ok=True)

        self.running = False
        self.stop_requested = False
        self.active_drivers = []
        self.drivers_lock = threading.Lock()

        # Stats Counters
        self.total_accounts = 0
        self.created_accounts = 0
        self.generated_videos = 0
        self.downloaded_videos = 0

        # Build AMOLED Glass UI
        self.ui = AppUI(
            window=self.window,
            default_folder=self.default_folder,
            on_start=self.start_pipeline,
            on_stop=self.stop_pipeline,
        )

        # Connect Logger to AMOLED Terminal
        self.logger = AppLogger(callback=self._log_to_ui)

        # Window Close Protocol
        self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _safe_ui(self, fn, *args, **kwargs):
        """Safely invoke widget update on the main Tkinter thread."""
        self.window.after(0, lambda: fn(*args, **kwargs))

    def _log_to_ui(self, formatted_message: str, level: str):
        self._safe_ui(self.ui.log_terminal.append_log, formatted_message, level)

    def _track_driver(self, driver):
        with self.drivers_lock:
            if driver not in self.active_drivers:
                self.active_drivers.append(driver)

    def _close_all_drivers(self) -> int:
        with self.drivers_lock:
            drivers = list(self.active_drivers)
            self.active_drivers.clear()

        closed = 0
        for d in drivers:
            try:
                d.quit()
                closed += 1
            except Exception:
                pass
        return closed

    # ── PIPELINE FLOW ────────────────────────────────────────────────────────

    def start_pipeline(self):
        if self.running:
            return

        if not is_connected():
            messagebox.showerror("No Internet", "Koneksi internet tidak terdeteksi. Periksa jaringan Anda.")
            return

        prompts = self.ui.prompt_editor.get_prompts()
        if not prompts:
            messagebox.showwarning(
                "Prompt Kosong",
                "Masukkan minimal satu prompt video di kotak teks sebelum memulai.",
            )
            return

        dest_folder = self.ui.folder_var.get().strip() or self.default_folder
        os.makedirs(dest_folder, exist_ok=True)

        batches = calculate_batches(prompts, max_per_account=MAX_VIDEOS_PER_ACCOUNT)
        self.total_accounts = len(batches)
        self.created_accounts = 0
        self.generated_videos = 0
        self.downloaded_videos = 0

        self.running = True
        self.stop_requested = False
        self.ui.set_running_state(True)
        self.ui.stats_bar.update_stats(0, 0, 0)

        self.logger.info(
            f"Memulai pipeline: {len(prompts)} prompt dibagi ke dalam {self.total_accounts} akun (maks {MAX_VIDEOS_PER_ACCOUNT} per akun)."
        )

        threading.Thread(
            target=self._worker_thread,
            args=(batches, dest_folder, len(prompts)),
            daemon=True,
        ).start()

    def stop_pipeline(self):
        if not self.running:
            return

        self.stop_requested = True
        self.logger.warn("Permintaan stop diterima. Menghentikan pipeline dan membersihkan browser...")
        self.ui.stop_btn.configure(state="disabled")

        threading.Thread(target=self._stop_and_cleanup, daemon=True).start()

    def _stop_and_cleanup(self):
        closed = self._close_all_drivers()
        self.running = False
        self._safe_ui(self.ui.set_running_state, False)
        self.logger.warn(f"Pipeline dihentikan. {closed} browser aktif ditutup.")

    def _worker_thread(self, batches: List[dict], dest_folder: str, total_prompts: int):
        def on_acc_created(acc_info):
            self.created_accounts += 1
            self._safe_ui(
                self.ui.stats_bar.update_stats,
                self.created_accounts,
                self.generated_videos,
                self.downloaded_videos,
            )

        def on_video_gen():
            self.generated_videos += 1
            self._safe_ui(
                self.ui.stats_bar.update_stats,
                self.created_accounts,
                self.generated_videos,
                self.downloaded_videos,
            )

        def on_video_dl():
            self.downloaded_videos += 1
            self._safe_ui(
                self.ui.stats_bar.update_stats,
                self.created_accounts,
                self.generated_videos,
                self.downloaded_videos,
            )

        for batch in batches:
            if self.stop_requested:
                break

            acc_idx = batch["account_index"]
            batch_prompts = batch["prompts"]

            self.logger.info(f"--- Menjalankan Batch Akun #{acc_idx} ({len(batch_prompts)} prompt) ---")

            worker = AccountPipelineWorker(
                account_index=acc_idx,
                prompts=batch_prompts,
                download_folder=dest_folder,
                log_callback=self.logger.info,
                stop_check=lambda: self.stop_requested,
                driver_tracker_callback=self._track_driver,
                on_account_created=on_acc_created,
                on_video_generated=on_video_gen,
                on_video_downloaded=on_video_dl,
            )

            try:
                worker.run()
            except Exception as e:
                self.logger.error(f"[Akun #{acc_idx}] Terjadi kesalahan: {e}")

        self.running = False
        self._safe_ui(self._on_pipeline_completed, self.downloaded_videos, total_prompts, dest_folder)

    def _on_pipeline_completed(self, downloaded: int, total: int, folder: str):
        self.ui.set_running_state(False)
        self._close_all_drivers()

        if self.stop_requested:
            self.logger.warn(f"Pipeline selesai dengan penghentian. Unduhan: {downloaded}/{total}.")
        else:
            self.logger.success(f"Pipeline tuntas 100%! Semua {downloaded}/{total} video berhasil diunduh.")
            messagebox.showinfo(
                "AutoPix Selesai",
                f"Seluruh proses otomatis selesai!\n\n"
                f"Video Berhasil Diunduh: {downloaded}/{total}\n"
                f"Tersimpan di: {folder}",
            )

    def _on_window_close(self):
        self.stop_requested = True
        self.running = False
        try:
            self._close_all_drivers()
        except Exception:
            pass
        self.window.destroy()

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    app = AutoPixApp()
    app.run()

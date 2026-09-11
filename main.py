import ctypes
import os
import threading
from tkinter import messagebox

import customtkinter as ctk

from config import (
    APP_ID,
    APP_NAME,
    APP_VERSION,
    DEFAULT_DOWNLOAD_FOLDER,
)
from core import (
    AccountPipelineWorker,
    calculate_batches,
    is_connected,
    parse_prompts,
)
from ui import AppUI

# Windows Taskbar Icon AppUserModelID
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
except Exception:
    pass


class AutoPixApp:
    """Master Application Controller for AutoPix: Prompt-to-Video Automatic Pipeline."""

    def __init__(self):
        self.window = ctk.CTk()

        # State Variables
        self.status_var = ctk.StringVar(value="STANDBY")
        self.default_folder = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            DEFAULT_DOWNLOAD_FOLDER,
        )

        self.running = False
        self.stop_requested = False
        self.active_drivers = []
        self.drivers_lock = threading.Lock()

        self.ui = AppUI(
            self.window,
            app_name=APP_NAME,
            app_version=APP_VERSION,
            status_var=self.status_var,
            default_folder=self.default_folder,
            on_start=self.start_pipeline,
            on_stop=self.stop_pipeline,
        )

        self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _safe_ui(self, fn, *args, **kwargs):
        """Invoke a function on the main Tkinter thread safely."""
        self.window.after(0, lambda: fn(*args, **kwargs))

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

    # ── PIPELINE EXECUTION ───────────────────────────────────────────────────

    def start_pipeline(self):
        if self.running:
            return

        if not is_connected():
            messagebox.showerror("No Internet", "Koneksi internet tidak terdeteksi.")
            return

        raw_text = self.ui.prompt_box.get("1.0", "end-1c")
        prompts = parse_prompts(raw_text)

        if not prompts:
            messagebox.showwarning(
                "Prompt Kosong",
                "Masukkan minimal satu prompt video di kotak teks sebelum memulai.",
            )
            return

        batches = calculate_batches(prompts, max_per_account=3)
        total_accounts = len(batches)
        total_prompts = len(prompts)

        self.running = True
        self.stop_requested = False

        # Reset Stats & UI Controls
        self.ui.start_btn.configure(state="disabled")
        self.ui.stop_btn.configure(state="normal")
        self.ui.set_status("RUNNING")

        self.ui.stat_prompts.configure(text=str(total_prompts))
        self.ui.stat_accounts.configure(text=str(total_accounts))
        self.ui.stat_accounts_done.configure(text="0")
        self.ui.stat_videos_done.configure(text="0")

        self.ui.progress_bar.set(0)
        self.ui.progress_pct.configure(text="0%")

        self.ui.log(
            f"Memulai pipeline otomatis: {total_prompts} prompt terbagi ke dalam {total_accounts} akun (maks 3 video/akun)..."
        )

        threading.Thread(
            target=self._pipeline_worker,
            args=(batches, total_prompts),
            daemon=True,
        ).start()

    def stop_pipeline(self):
        if not self.running:
            return

        self.stop_requested = True
        self.ui.stop_btn.configure(state="disabled")
        self.ui.set_status("STOPPING")
        self.ui.log("Menghentikan pipeline & menutup browser aktif...")

        threading.Thread(target=self._stop_and_cleanup, daemon=True).start()

    def _stop_and_cleanup(self):
        closed = self._close_all_drivers()
        self.running = False
        self._safe_ui(self.ui.set_status, "STOPPED")
        self._safe_ui(self.ui.start_btn.configure, state="normal")
        self._safe_ui(self.ui.log, f"Pipeline dihentikan. {closed} browser aktif ditutup.")

    def _pipeline_worker(self, batches: list, total_prompts: int):
        accounts_done = 0
        videos_downloaded = 0
        total_accounts = len(batches)

        def on_acc_created(acc_info):
            nonlocal accounts_done
            accounts_done += 1
            self._safe_ui(self.ui.stat_accounts_done.configure, text=f"{accounts_done}/{total_accounts}")

        def on_video_download():
            nonlocal videos_downloaded
            videos_downloaded += 1
            self._safe_ui(self.ui.stat_videos_done.configure, text=f"{videos_downloaded}/{total_prompts}")
            pct = min(1.0, videos_downloaded / total_prompts if total_prompts else 0)
            self._safe_ui(self.ui.progress_bar.set, pct)
            self._safe_ui(self.ui.progress_pct.configure, text=f"{int(pct * 100)}%")

        for batch in batches:
            if self.stop_requested:
                break

            acc_idx = batch["account_index"]
            batch_prompts = batch["prompts"]

            self._safe_ui(
                self.ui.log,
                f"--- Memproses Akun #{acc_idx} ({len(batch_prompts)} prompt) ---",
            )

            worker = AccountPipelineWorker(
                account_index=acc_idx,
                prompts=batch_prompts,
                download_folder=self.ui.download_folder,
                log_callback=lambda m: self._safe_ui(self.ui.log, m),
                stop_check=lambda: self.stop_requested,
                driver_tracker_callback=self._track_driver,
                on_account_created=on_acc_created,
                on_video_downloaded=on_video_download,
            )

            try:
                worker.run()
            except Exception as e:
                self._safe_ui(self.ui.log, f"[Akun {acc_idx}] Error: {e}")

        self.running = False
        self._safe_ui(self._on_pipeline_finished, videos_downloaded, total_prompts)

    def _on_pipeline_finished(self, downloaded: int, total: int):
        self.ui.start_btn.configure(state="normal")
        self.ui.stop_btn.configure(state="disabled")

        if self.stop_requested:
            self.ui.set_status("STOPPED")
            self.ui.log(f"Pipeline berhenti. Video diunduh: {downloaded}/{total}.")
        else:
            self.ui.set_status("DONE")
            self.ui.progress_bar.set(1.0)
            self.ui.progress_pct.configure(text="100%")
            self.ui.log(f"🎉 Pipeline selesai! Total video berhasil diunduh: {downloaded}/{total}.")
            messagebox.showinfo(
                "AutoPix Selesai",
                f"Proses otomatis selesai!\n\n"
                f"Total Video Terunduh: {downloaded}/{total}\n"
                f"Folder: {self.ui.download_folder}",
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

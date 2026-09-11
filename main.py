from concurrent.futures import ThreadPoolExecutor, as_completed
import ctypes
import os
import re
import threading
import time
from tkinter import filedialog, messagebox

import customtkinter as ctk

from config import (
    APP_ID,
    APP_NAME,
    APP_VERSION,
    BROWSER_LAUNCH_STAGGER_DELAY,
    DEFAULT_DOWNLOAD_FOLDER,
)
from core import (
    PixVerseAccountCreator,
    PixVerseVideoDownloader,
    PixVerseVideoGenerator,
    is_connected,
    random_password,
)
from ui import AppUI

# Windows Taskbar Icon AppUserModelID
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
except Exception:
    pass


class AutoPixApp:
    """Master Application Controller for AutoPix Desktop Automation."""

    def __init__(self):
        self.window = ctk.CTk()

        # State Variables
        self.pixverse_count_var = ctk.StringVar(value="5")
        self.status_var = ctk.StringVar(value="STANDBY")
        self.download_folder = os.path.join(os.path.abspath(os.path.dirname(__file__)), DEFAULT_DOWNLOAD_FOLDER)

        # Account Generation State
        self.pixverse_running = False
        self.pixverse_stop_requested = False
        self.pixverse_success_count = 0
        self.pixverse_fail_count = 0
        self.pixverse_total_count = 0
        self.pixverse_drivers = []
        self.pixverse_driver_lock = threading.Lock()
        self.pixverse_accounts = []
        self.pixverse_accounts_lock = threading.Lock()

        # Video Generation State
        self.gen_running = False
        self.gen_stop_requested = False
        self.gen_total = 0
        self.gen_done = 0

        # Video Download State
        self.download_running = False
        self.download_stop_requested = False

        # Build UI
        callbacks = {
            "start_account": self.start_account_creation,
            "stop_account": self.stop_account_creation,
            "start_gen": self.start_video_generation,
            "stop_gen": self.stop_video_generation,
            "pick_folder": self.pick_download_folder,
            "start_download": self.start_video_download,
        }
        self.ui = AppUI(
            self.window,
            app_name=APP_NAME,
            app_version=APP_VERSION,
            count_var=self.pixverse_count_var,
            status_var=self.status_var,
            default_folder=self.download_folder,
            callbacks=callbacks,
        )

        self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _safe_ui(self, fn, *args, **kwargs):
        """Invoke a callable on the main Tkinter thread."""
        self.window.after(0, lambda: fn(*args, **kwargs))

    # ── 1. ACCOUNT CREATION FLOW ─────────────────────────────────────────────

    def start_account_creation(self):
        if self.pixverse_running:
            return

        if not is_connected():
            messagebox.showerror("No Internet", "Tidak ada koneksi internet.")
            return

        try:
            count = max(1, min(100, int(self.pixverse_count_var.get().strip())))
        except Exception:
            count = 5
        self.pixverse_count_var.set(str(count))

        self.pixverse_running = True
        self.pixverse_stop_requested = False
        self.pixverse_success_count = 0
        self.pixverse_fail_count = 0
        self.pixverse_total_count = count

        with self.pixverse_driver_lock:
            self.pixverse_drivers.clear()
        with self.pixverse_accounts_lock:
            self.pixverse_accounts.clear()

        # Reset UI
        self.ui.tab_akun.stat_target.configure(text=str(count))
        self.ui.tab_akun.stat_success.configure(text="0")
        self.ui.tab_akun.stat_fail.configure(text="0")
        self.ui.progress_bar.set(0)
        self.ui.progress_pct.configure(text="0%")

        self.ui.tab_akun.start_btn.configure(state="disabled")
        self.ui.tab_akun.stop_btn.configure(state="normal")
        self.ui.set_status("RUNNING")
        self.ui.log(f"Mulai {count} akun — seluruh browser dibuka bertahap...")

        threading.Thread(
            target=self._account_worker,
            args=(count,),
            daemon=True,
        ).start()

    def stop_account_creation(self):
        self.ui.tab_akun.stop_btn.configure(state="disabled")

        if self.pixverse_running:
            self.pixverse_stop_requested = True
            self.ui.set_status("STOPPING")
            self.ui.log("Menghentikan proses & menutup browser...")
            closed = self._close_all_registered_drivers()
            self.ui.log(f"{closed} browser aktif berhasil ditutup.")
        else:
            closed = self._close_all_registered_drivers()
            self.ui.log(f"Pembersihan: {closed} browser ditutup.")
            self.ui.progress_bar.set(0)
            self.ui.progress_pct.configure(text="0%")
            self.ui.set_status("STANDBY")
            self.ui.tab_akun.start_btn.configure(state="normal")

    def _account_worker(self, count: int):
        stats_lock = threading.Lock()

        def register_driver(d):
            with self.pixverse_driver_lock:
                if d not in self.pixverse_drivers:
                    self.pixverse_drivers.append(d)

        def single_task(idx):
            if self.pixverse_stop_requested:
                return

            pwd = random_password(12)
            self._safe_ui(self.ui.log, f"[Akun {idx}] Memulai pendaftaran...")

            creator = PixVerseAccountCreator(
                log_callback=lambda m: self._safe_ui(self.ui.log, m),
                stop_check=lambda: self.pixverse_stop_requested,
                driver_opened_callback=register_driver,
            )

            try:
                ok, email, driver = creator.create_account(idx, pwd)
            except Exception as e:
                ok, email, driver = False, None, None
                self._safe_ui(self.ui.log, f"[Akun {idx}] Exception: {e}")

            with stats_lock:
                if ok and email and driver:
                    self.pixverse_success_count += 1
                    self._safe_ui(self.ui.log, f"[Akun {idx}] Sukses! Email: {email}")
                    with self.pixverse_accounts_lock:
                        self.pixverse_accounts.append({
                            "index": idx,
                            "email": email,
                            "driver": driver,
                        })
                else:
                    self.pixverse_fail_count += 1
                    self._safe_ui(self.ui.log, f"[Akun {idx}] Pendaftaran gagal.")

                done = self.pixverse_success_count + self.pixverse_fail_count
                self._safe_ui(self._update_account_progress, done, count)

        try:
            with ThreadPoolExecutor(max_workers=count) as executor:
                futures = {}
                for idx in range(1, count + 1):
                    if self.pixverse_stop_requested:
                        break
                    futures[executor.submit(single_task, idx)] = idx
                    if idx < count:
                        time.sleep(BROWSER_LAUNCH_STAGGER_DELAY)

                for future in as_completed(futures):
                    if self.pixverse_stop_requested:
                        break
                    try:
                        future.result()
                    except Exception:
                        pass
        except Exception as e:
            if not self.pixverse_stop_requested:
                self._safe_ui(self.ui.log, f"Worker error: {e}")
        finally:
            self.pixverse_running = False
            self._safe_ui(self._finish_account_creation)

    def _update_account_progress(self, completed: int, total: int):
        self.ui.tab_akun.stat_success.configure(text=str(self.pixverse_success_count))
        self.ui.tab_akun.stat_fail.configure(text=str(self.pixverse_fail_count))
        pct = completed / total if total else 0
        self.ui.progress_bar.set(pct)
        self.ui.progress_pct.configure(text=f"{int(pct * 100)}%")

    def _finish_account_creation(self):
        self.ui.tab_akun.start_btn.configure(state="normal")

        if self.pixverse_stop_requested:
            self.ui.set_status("STOPPED")
            msg = (
                f"Proses dihentikan.\n\n"
                f"Selesai: {self.pixverse_success_count + self.pixverse_fail_count}/{self.pixverse_total_count}\n"
                f"Berhasil: {self.pixverse_success_count} -- Gagal: {self.pixverse_fail_count}"
            )
        else:
            self.ui.tab_akun.stop_btn.configure(state="normal")
            self.ui.set_status("DONE")
            msg = (
                f"Proses pendaftaran selesai.\n\n"
                f"Berhasil: {self.pixverse_success_count}/{self.pixverse_total_count}\n"
                f"Gagal: {self.pixverse_fail_count}/{self.pixverse_total_count}\n\n"
                f"Browser tetap terbuka untuk tab generate."
            )

        self.ui.log("Proses pendaftaran selesai.")
        messagebox.showinfo("PixVerse Creator", msg)

    def _close_all_registered_drivers(self) -> int:
        with self.pixverse_driver_lock:
            active = list(self.pixverse_drivers)
            self.pixverse_drivers.clear()

        closed = 0
        for d in active:
            try:
                d.quit()
                closed += 1
            except Exception:
                pass
        return closed

    # ── 2. VIDEO GENERATION FLOW ─────────────────────────────────────────────

    def start_video_generation(self):
        if self.gen_running:
            return

        raw = self.ui.tab_gen.prompt_textbox.get("1.0", "end-1c").strip()
        all_prompts = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]

        if not all_prompts:
            messagebox.showwarning(
                "Generate Video",
                "Masukkan minimal satu prompt video terlebih dahulu (pisahkan dengan baris kosong).",
            )
            return

        with self.pixverse_accounts_lock:
            accounts_copy = sorted(self.pixverse_accounts, key=lambda x: x["index"])

        if not accounts_copy:
            messagebox.showwarning(
                "Generate Video",
                "Tidak ada akun aktif yang tersedia.\nBuat akun terlebih dahulu pada tab Buat Akun.",
            )
            return

        alive_accounts = []
        for acc in accounts_copy:
            try:
                _ = acc["driver"].current_url
                alive_accounts.append(acc)
            except Exception:
                self.ui.log(f"[Akun {acc['index']}] Browser sudah tertutup, lewati.")

        if not alive_accounts:
            messagebox.showwarning(
                "Generate Video",
                "Semua browser sudah tertutup.\nTidak bisa generate tanpa sesi browser aktif.",
            )
            return

        # Distribusi prompt round-robin ke akun-akun yang hidup
        account_prompts = {}
        for i, acc in enumerate(alive_accounts):
            idx = acc["index"]
            account_prompts[idx] = all_prompts[i :: len(alive_accounts)]

        self.gen_running = True
        self.gen_stop_requested = False
        self.gen_total = len(all_prompts)
        self.gen_done = 0

        self.ui.tab_gen.gen_start_btn.configure(state="disabled")
        self.ui.tab_gen.gen_stop_btn.configure(state="normal")
        self.ui.set_status("RUNNING")
        self.ui.progress_bar.set(0)
        self.ui.progress_pct.configure(text="0%")
        self.ui.log(f"Mulai generate {self.gen_total} video dari {len(alive_accounts)} akun aktif...")

        threading.Thread(
            target=self._video_generate_worker,
            args=(alive_accounts, account_prompts),
            daemon=True,
        ).start()

    def stop_video_generation(self):
        self.ui.tab_gen.gen_stop_btn.configure(state="disabled")
        if self.gen_running:
            self.gen_stop_requested = True
            self.ui.set_status("STOPPING")
            self.ui.log("Menghentikan generate video...")

    def _video_generate_worker(self, accounts: list, account_prompts: dict):
        gen_lock = threading.Lock()

        def task_for_account(acc):
            idx = acc["index"]
            driver = acc["driver"]
            email = acc.get("email", "?")

            self._safe_ui(self.ui.log, f"[Akun {idx}] Mulai memproses video ({email})...")

            generator = PixVerseVideoGenerator(
                driver,
                log_callback=lambda m: self._safe_ui(self.ui.log, m),
                stop_check=lambda: self.gen_stop_requested,
            )

            prompts = account_prompts.get(idx, [])
            for vid_num, prompt in enumerate(prompts, start=1):
                if self.gen_stop_requested:
                    break

                if not prompt.strip():
                    with gen_lock:
                        self.gen_done += 1
                    self._safe_ui(self._update_gen_progress)
                    continue

                preview = prompt[:45] + ("..." if len(prompt) > 45 else "")
                self._safe_ui(self.ui.log, f"[Akun {idx}] Video {vid_num}/{len(prompts)} -> {preview}")

                ok = generator.generate_video(prompt_text=prompt)
                with gen_lock:
                    self.gen_done += 1

                status_label = "Sukses" if ok else "Gagal"
                self._safe_ui(self.ui.log, f"[Akun {idx}] Video {vid_num}/{len(prompts)} {status_label}")
                self._safe_ui(self._update_gen_progress)

                if vid_num < len(prompts) and not self.gen_stop_requested:
                    time.sleep(5)

        try:
            with ThreadPoolExecutor(max_workers=len(accounts)) as executor:
                futures = {executor.submit(task_for_account, acc): acc["index"] for acc in accounts}
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        self._safe_ui(self.ui.log, f"[Akun {idx}] Error: {e}")
        except Exception as e:
            self._safe_ui(self.ui.log, f"Worker error: {e}")
        finally:
            self.gen_running = False
            self._safe_ui(self._finish_video_generation)

    def _update_gen_progress(self):
        pct = self.gen_done / self.gen_total if self.gen_total else 0
        self.ui.progress_bar.set(pct)
        self.ui.progress_pct.configure(text=f"{int(pct * 100)}% ({self.gen_done}/{self.gen_total} video)")

    def _finish_video_generation(self):
        self.ui.tab_gen.gen_start_btn.configure(state="normal")
        self.ui.tab_gen.gen_stop_btn.configure(state="disabled")

        if self.gen_stop_requested:
            self.ui.set_status("STOPPED")
            self.ui.log("Generate video dihentikan oleh pengguna.")
        else:
            self.ui.set_status("DONE")
            self.ui.log(f"Generate video selesai: {self.gen_done}/{self.gen_total} video diproses.")
            messagebox.showinfo(
                "Generate Video",
                f"Proses generate selesai!\n\n"
                f"Total video diproses: {self.gen_done}/{self.gen_total}\n\n"
                f"Gunakan tab Download untuk mengunduh seluruh hasilnya.",
            )

    # ── 3. VIDEO DOWNLOAD FLOW ───────────────────────────────────────────────

    def pick_download_folder(self):
        folder = filedialog.askdirectory(
            title="Pilih Folder Penyimpanan Video",
            initialdir=self.download_folder,
        )
        if folder:
            self.download_folder = folder
            self.ui.tab_dl.folder_path_label.configure(
                text=self.ui.tab_dl._truncate_path(folder)
            )
            self.ui.log(f"Folder download diperbarui: {folder}")

    def start_video_download(self):
        if self.download_running:
            return

        with self.pixverse_accounts_lock:
            accounts_copy = sorted(self.pixverse_accounts, key=lambda x: x["index"])

        if not accounts_copy:
            messagebox.showwarning(
                "Download Video",
                "Tidak ada akun aktif.\nBuat akun dan generate video terlebih dahulu.",
            )
            return

        alive_accounts = []
        for acc in accounts_copy:
            try:
                _ = acc["driver"].current_url
                alive_accounts.append(acc)
            except Exception:
                self.ui.log(f"[Akun {acc['index']}] Browser sudah tertutup, lewati.")

        if not alive_accounts:
            messagebox.showwarning(
                "Download Video",
                "Semua browser sudah tertutup.\nTidak bisa download tanpa sesi aktif.",
            )
            return

        self.download_running = True
        self.download_stop_requested = False
        self.ui.tab_dl.download_all_btn.configure(state="disabled", text="DOWNLOADING...")
        self.ui.set_status("DOWNLOADING")
        self.ui.log(f"Memulai pengunduhan video dari {len(alive_accounts)} akun aktif...")

        threading.Thread(
            target=self._video_download_worker,
            args=(alive_accounts,),
            daemon=True,
        ).start()

    def _video_download_worker(self, accounts: list):
        try:
            downloader = PixVerseVideoDownloader(
                log_callback=lambda m: self._safe_ui(self.ui.log, m),
                stop_check=lambda: self.download_stop_requested,
            )
            success, fail = downloader.download_all(accounts, self.download_folder)

            def on_finish():
                self.download_running = False
                self.ui.tab_dl.download_all_btn.configure(state="normal", text="Download")
                self.ui.set_status("DONE")
                messagebox.showinfo(
                    "Download Video",
                    f"Pengunduhan selesai!\n\n"
                    f"Berhasil: {success}\n"
                    f"Gagal: {fail}\n\n"
                    f"Lokasi: {self.download_folder}",
                )

            self._safe_ui(on_finish)

        except Exception as e:
            def on_error():
                self.download_running = False
                self.ui.tab_dl.download_all_btn.configure(state="normal", text="Download")
                self.ui.set_status("DONE")
                self.ui.log(f"Download error: {e}")

            self._safe_ui(on_error)

    def _on_window_close(self):
        """Clean close on exit."""
        self.pixverse_stop_requested = True
        self.gen_stop_requested = True
        self.download_stop_requested = True
        self._close_all_registered_drivers()
        self.window.destroy()

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    app = AutoPixApp()
    app.run()

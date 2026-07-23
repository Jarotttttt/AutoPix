import os
import re
import sys
import threading
import time
from datetime import datetime
from tkinter import messagebox, filedialog

import customtkinter as ctk
import tksvg

from core.pixverse_creator import PixVerseAccountCreator, is_connected
from core.video_downloader import PixVerseVideoDownloader
from core.pixverse_video_generator import PixVerseVideoGenerator
import warnings
warnings.filterwarnings("ignore", message=".*Given image is not CTkImage.*")

APP_NAME    = "AutoPix"
APP_VERSION = "v3.0"

BG_COLOR     = "#0A0A0C"
CARD_BG      = "#121215"
BORDER_COLOR = "#222226"
TEXT_MAIN    = "#FAFAFA"
TEXT_MUTED   = "#71717A"
ACCENT_BLUE  = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
RED_COLOR    = "#E11D48"
RED_HOVER    = "#BE123C"
GREEN_COLOR  = "#10B981"
PURPLE_COLOR = "#7C3AED"
PURPLE_HOVER = "#6D28D9"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class App:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title(f"{APP_NAME} | {APP_VERSION}")
        self.window.geometry("1100x720")
        self.window.minsize(950, 620)
        self.window.configure(fg_color=BG_COLOR)

        try:
            self.window.iconbitmap(resource_path("ai.ico"))
        except Exception:
            pass

        self.pixverse_count_var = ctk.StringVar(value="5")
        self.status_var         = ctk.StringVar(value="STANDBY")

        self.pixverse_running        = False
        self.pixverse_stop_requested = False
        self.pixverse_success_count  = 0
        self.pixverse_fail_count     = 0
        self.pixverse_total_count    = 0

        self.pixverse_drivers     = []
        self.pixverse_driver_lock = threading.Lock()

        self.prompt_textbox = None
        self.gen_running  = False
        self.gen_stop_req = False
        self.gen_total    = 0
        self.gen_done     = 0

        self.download_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
        self.pixverse_accounts       = []
        self.pixverse_accounts_lock  = threading.Lock()
        self.download_running        = False
        self.download_stop_requested = False

        self._build_ui()
        self._tick_clock()

    def _build_ui(self):
        self.window.grid_columnconfigure(1, weight=1)
        self.window.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        sidebar = ctk.CTkFrame(self.window, fg_color=CARD_BG, corner_radius=0, width=220)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_rowconfigure(5, weight=1)
        
        brand_lbl = ctk.CTkLabel(sidebar, text=APP_NAME.upper(), font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        brand_lbl.grid(row=0, column=0, padx=20, pady=(24, 2), sticky="w")
        version_lbl = ctk.CTkLabel(sidebar, text=f"{APP_VERSION}", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=PURPLE_COLOR)
        version_lbl.grid(row=1, column=0, padx=20, pady=(0, 32), sticky="w")
        
        self.svg_user = tksvg.SvgImage(file="assets/user.svg", scaletowidth=18)
        self.svg_video = tksvg.SvgImage(file="assets/video.svg", scaletowidth=18)
        self.svg_dl = tksvg.SvgImage(file="assets/download.svg", scaletowidth=18)

        btn_font = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        self.btn_akun = ctk.CTkButton(sidebar, text="  Buat Akun", image=self.svg_user, anchor="w", fg_color="transparent", text_color=TEXT_MUTED, hover_color="#222226", command=lambda: self.select_tab("akun"), font=btn_font, height=40)
        self.btn_akun.grid(row=2, column=0, sticky="ew", padx=12, pady=4)
        
        self.btn_gen = ctk.CTkButton(sidebar, text="  Generate Video", image=self.svg_video, anchor="w", fg_color="transparent", text_color=TEXT_MUTED, hover_color="#222226", command=lambda: self.select_tab("gen"), font=btn_font, height=40)
        self.btn_gen.grid(row=3, column=0, sticky="ew", padx=12, pady=4)
        
        self.btn_dl = ctk.CTkButton(sidebar, text="  Download", image=self.svg_dl, anchor="w", fg_color="transparent", text_color=TEXT_MUTED, hover_color="#222226", command=lambda: self.select_tab("dl"), font=btn_font, height=40)
        self.btn_dl.grid(row=4, column=0, sticky="ew", padx=12, pady=4)
        
        # Status & Clock at bottom
        self.status_badge = ctk.CTkLabel(sidebar, textvariable=self.status_var, font=ctk.CTkFont(size=11, weight="bold"), text_color="#FFF", fg_color=ACCENT_BLUE, corner_radius=6, height=28)
        self.status_badge.grid(row=5, column=0, sticky="sw", padx=20, pady=(0, 8))
        
        self.clock_label = ctk.CTkLabel(sidebar, text="", font=ctk.CTkFont(family="Consolas", size=12), text_color=TEXT_MUTED)
        self.clock_label.grid(row=6, column=0, sticky="sw", padx=20, pady=(0, 24))
        
        # --- Main Content ---
        main_content = ctk.CTkFrame(self.window, fg_color="transparent")
        main_content.grid(row=0, column=1, sticky="nsew", padx=24, pady=24)
        main_content.grid_columnconfigure(0, weight=4)
        main_content.grid_columnconfigure(1, weight=5)
        main_content.grid_rowconfigure(0, weight=1)
        
        self.frame_akun = ctk.CTkFrame(main_content, fg_color="transparent")
        self.frame_gen = ctk.CTkFrame(main_content, fg_color="transparent")
        self.frame_dl = ctk.CTkFrame(main_content, fg_color="transparent")
        
        self._build_tab_akun(self.frame_akun)
        self._build_tab_generate(self.frame_gen)
        self._build_tab_download(self.frame_dl)
        
        self.frames = {"akun": self.frame_akun, "gen": self.frame_gen, "dl": self.frame_dl}
        self.btns = {"akun": self.btn_akun, "gen": self.btn_gen, "dl": self.btn_dl}
        
        self._build_monitor(main_content)
        
        self.select_tab("akun")

    def select_tab(self, tab_name):
        for name, frame in self.frames.items():
            if name == tab_name:
                frame.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
                self.btns[name].configure(fg_color=PURPLE_COLOR, text_color="#FFF")
            else:
                frame.grid_forget()
                self.btns[name].configure(fg_color="transparent", text_color=TEXT_MUTED)

    def _build_tab_akun(self, parent):
        parent.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            parent, text="Pengaturan Akun", 
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), 
            text_color=TEXT_MAIN
        ).grid(row=0, column=0, sticky="w", pady=(10, 14))

        stats_row = ctk.CTkFrame(parent, fg_color="transparent")
        stats_row.grid(row=1, column=0, sticky="ew", pady=(0, 24))
        stats_row.grid_columnconfigure((0, 1, 2), weight=1)
        self.pixverse_total_lbl   = self._stat_card(stats_row, 0, "TARGET",  "0", TEXT_MAIN)
        self.pixverse_success_lbl = self._stat_card(stats_row, 1, "BERHASIL", "0", GREEN_COLOR)
        self.pixverse_fail_lbl    = self._stat_card(stats_row, 2, "GAGAL",   "0", RED_COLOR)

        lbl_kw   = dict(font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_MUTED)
        entry_kw = dict(fg_color=BG_COLOR, border_color=BORDER_COLOR, text_color=TEXT_MAIN,
                        corner_radius=10, height=42, font=ctk.CTkFont(family="Segoe UI", size=14))

        ctk.CTkLabel(parent, text="Jumlah Akun", **lbl_kw).grid(
            row=2, column=0, sticky="w", pady=(0, 6))
        ctk.CTkEntry(parent, textvariable=self.pixverse_count_var, **entry_kw).grid(
            row=3, column=0, sticky="ew", pady=(0, 28))

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self.pixverse_start_btn = ctk.CTkButton(
            btn_row, text="Mulai", command=self.start_pixverse,
            fg_color=ACCENT_BLUE, hover_color=ACCENT_HOVER,
            text_color="#FFF", height=46, corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        )
        self.pixverse_start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.pixverse_stop_btn = ctk.CTkButton(
            btn_row, text="Berhenti", command=self.stop_pixverse,
            fg_color=RED_COLOR, hover_color=RED_HOVER,
            text_color="#FFF", height=46, corner_radius=10, state="disabled",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        )
        self.pixverse_stop_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _build_tab_generate(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            parent, text="Prompt Video", 
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), 
            text_color=TEXT_MAIN
        ).grid(row=0, column=0, sticky="w", pady=(10, 10))

        self.prompt_textbox = ctk.CTkTextbox(
            parent, fg_color=CARD_BG, border_color=BORDER_COLOR, text_color=TEXT_MAIN,
            corner_radius=8, border_width=1,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.prompt_textbox.grid(row=1, column=0, sticky="nsew", pady=(0, 20))
        self.prompt_textbox.insert("1.0", "Masukkan prompt di sini.\nPisahkan dengan baris kosong.")

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew")
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self.gen_start_btn = ctk.CTkButton(
            btn_row, text="Generate", command=self.start_video_generate,
            fg_color=PURPLE_COLOR, hover_color=PURPLE_HOVER,
            text_color="#FFF", height=46, corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        )
        self.gen_start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.gen_stop_btn = ctk.CTkButton(
            btn_row, text="Berhenti", command=self.stop_video_generate,
            fg_color=RED_COLOR, hover_color=RED_HOVER,
            text_color="#FFF", height=46, corner_radius=10, state="disabled",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        )
        self.gen_stop_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _build_tab_download(self, parent):
        parent.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            parent, text="Penyimpanan Video", 
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), 
            text_color=TEXT_MAIN
        ).grid(row=0, column=0, sticky="w", pady=(10, 14))

        card_folder = ctk.CTkFrame(parent, fg_color=BG_COLOR, corner_radius=12, border_width=1, border_color=BORDER_COLOR)
        card_folder.grid(row=1, column=0, sticky="ew", pady=(0, 24), padx=2)
        card_folder.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card_folder, text="LOKASI FOLDER",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=16, pady=(14, 4))

        self.folder_path_label = ctk.CTkLabel(
            card_folder,
            text=self._truncate_path(self.download_folder),
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=TEXT_MAIN,
            wraplength=380,
            justify="left",
        )
        self.folder_path_label.pack(anchor="w", padx=16, pady=(0, 14))

        self.pick_folder_btn = ctk.CTkButton(
            parent, text="Pilih Folder", command=self.pick_download_folder,
            fg_color="#18181C", hover_color="#222226",
            text_color=TEXT_MAIN, height=42, corner_radius=10,
            border_width=1, border_color=BORDER_COLOR,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        )
        self.pick_folder_btn.grid(row=2, column=0, sticky="ew", pady=(0, 24))

        self.download_all_btn = ctk.CTkButton(
            parent, text="Download", command=self.start_video_download,
            fg_color=PURPLE_COLOR, hover_color=PURPLE_HOVER,
            text_color="#FFF", height=48, corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        )
        self.download_all_btn.grid(row=3, column=0, sticky="ew")

    def _build_monitor(self, parent):
        right = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=16,
                             border_color=BORDER_COLOR, border_width=1)
        right.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(right, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 8))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="Log Aktivitas",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, sticky="w")

        self.pixverse_progress_pct = ctk.CTkLabel(
            hdr, text="0%",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=PURPLE_COLOR,
        )
        self.pixverse_progress_pct.grid(row=0, column=1, sticky="e")

        self.pixverse_progress_bar = ctk.CTkProgressBar(
            right, progress_color=PURPLE_COLOR, fg_color=BG_COLOR, height=10, corner_radius=5
        )
        self.pixverse_progress_bar.set(0)
        self.pixverse_progress_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))

        self.pixverse_log_box = ctk.CTkTextbox(
            right, fg_color=BG_COLOR, text_color="#E4E4E7",
            border_color=BORDER_COLOR, border_width=1,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word", corner_radius=12,
        )
        self.pixverse_log_box.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.pixverse_log_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] Sistem Siap.\n")
        self.pixverse_log_box.configure(state="disabled")

    def _stat_card(self, parent, col, title, value, color):
        card = ctk.CTkFrame(parent, fg_color=BG_COLOR, corner_radius=12,
                            border_color=BORDER_COLOR, border_width=1)
        pad = (0, 8) if col < 2 else (0, 0)
        card.grid(row=0, column=col, sticky="ew", padx=pad)
        
        ctk.CTkLabel(card, text=title,
                     font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                     text_color=TEXT_MUTED).pack(pady=(12, 2))
                     
        lbl = ctk.CTkLabel(card, text=value,
                           font=ctk.CTkFont(family="Consolas", size=28, weight="bold"),
                           text_color=color)
        lbl.pack(pady=(0, 12))
        return lbl

    def _tick_clock(self):
        self.clock_label.configure(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.window.after(1000, self._tick_clock)

    def _set_status(self, text):
        self.status_var.set(text)
        color_map = {
            "STANDBY":     ACCENT_BLUE,
            "RUNNING":     "#F59E0B",
            "STOPPING":    RED_COLOR,
            "STOPPED":     "#991B1B",
            "DONE":        GREEN_COLOR,
            "DOWNLOADING": PURPLE_COLOR,
        }
        self.status_badge.configure(fg_color=color_map.get(text, ACCENT_BLUE))

    def _safe_ui(self, fn, *args, **kwargs):
        self.window.after(0, lambda: fn(*args, **kwargs))

    def _pixverse_append_log(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        self.pixverse_log_box.configure(state="normal")
        self.pixverse_log_box.insert("end", f"[{ts}] {message}\n")
        self.pixverse_log_box.see("end")
        self.pixverse_log_box.configure(state="disabled")

    def _pixverse_log(self, msg):
        self._safe_ui(self._pixverse_append_log, msg)

    @staticmethod
    def _truncate_path(path, max_len=40):
        if len(path) <= max_len:
            return path
        parts = path.replace("\\", "/").split("/")
        if len(parts) <= 2:
            return path
        return parts[0] + "/.../" + "/".join(parts[-2:])

    @staticmethod
    def _parse_int(raw, minimum, maximum, fallback):
        try:
            v = int(raw)
        except (TypeError, ValueError):
            return fallback
        return max(minimum, min(maximum, v))

    def start_pixverse(self):
        if self.pixverse_running:
            self._pixverse_append_log("Running.")
            return

        if not is_connected():
            messagebox.showerror("No Internet", "Tidak ada koneksi internet.")
            return

        count = self._parse_int(self.pixverse_count_var.get(), 1, 100, 5)
        self.pixverse_count_var.set(str(count))

        self.pixverse_running        = True
        self.pixverse_stop_requested = False
        self.pixverse_success_count  = self.pixverse_fail_count = 0
        self.pixverse_total_count    = count

        with self.pixverse_driver_lock:
            self.pixverse_drivers.clear()
        with self.pixverse_accounts_lock:
            self.pixverse_accounts.clear()

        self.pixverse_total_lbl.configure(text=str(count))
        self.pixverse_success_lbl.configure(text="0")
        self.pixverse_fail_lbl.configure(text="0")
        self.pixverse_progress_bar.set(0)
        self.pixverse_progress_pct.configure(text="0%")

        self.pixverse_log_box.configure(state="normal")
        self.pixverse_log_box.delete("1.0", "end")
        self.pixverse_log_box.configure(state="disabled")

        self.pixverse_start_btn.configure(state="disabled")
        self.pixverse_stop_btn.configure(state="normal")
        self._set_status("RUNNING")
        self._pixverse_append_log(f"Mulai {count} akun — semua browser jalan bersamaan.")

        threading.Thread(
            target=self._pixverse_worker,
            args=(count,),
            daemon=True,
        ).start()

    def stop_pixverse(self):
        self.pixverse_stop_btn.configure(state="disabled")

        if self.pixverse_running:
            self.pixverse_stop_requested = True
            self._set_status("STOPPING")
            self._pixverse_append_log("Menghentikan dan membersihkan browser...")
            closed_count = self._pixverse_force_stop_browsers()
            self._pixverse_append_log(f"{closed_count} browser aktif ditutup.")
        else:
            closed_count = self._pixverse_force_stop_browsers()
            self._pixverse_append_log(f"Pembersihan: {closed_count} browser ditutup.")
            self.pixverse_progress_bar.set(0)
            self.pixverse_progress_pct.configure(text="0%")
            self._set_status("STANDBY")
            self.pixverse_start_btn.configure(state="normal")

    def _pixverse_worker(self, count):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from core.pixverse_creator import random_password

        self.stats_lock = threading.Lock()

        def run_task(idx):
            if self.pixverse_stop_requested:
                return

            pwd = random_password(12)
            self._pixverse_log(f"[Akun {idx}] Memulai pendaftaran...")
            creator = PixVerseAccountCreator(
                log_callback=self._pixverse_log,
                stop_check=lambda: self.pixverse_stop_requested,
                driver_opened_callback=self._pixverse_register_driver,
            )

            try:
                ok, email, driver = creator.create_account(idx, pwd)
            except Exception as e:
                ok, email, driver = False, None, None
                self._pixverse_log(f"[Akun {idx}] Gagal: {e}")

            with self.stats_lock:
                if ok and email and driver:
                    self.pixverse_success_count += 1
                    self._pixverse_log(f"[Akun {idx}] Sukses dibuat! Email: {email} | Password: {pwd}")
                    with self.pixverse_accounts_lock:
                        self.pixverse_accounts.append({
                            "index": idx,
                            "email": email,
                            "driver": driver,
                        })
                else:
                    self.pixverse_fail_count += 1
                    self._pixverse_log(f"[Akun {idx}] Pendaftaran gagal.")

                completed = self.pixverse_success_count + self.pixverse_fail_count
                self._safe_ui(self._pixverse_update_progress, completed, count)

        try:
            # Stagger launch delay
            # Kecepatan tunggu jeda antar browser tetap dipertahankan
            STAGGER_DELAY = 2.5
            with ThreadPoolExecutor(max_workers=count) as executor:
                futures = {}
                for idx in range(1, count + 1):
                    if self.pixverse_stop_requested:
                        break
                    futures[executor.submit(run_task, idx)] = idx
                    if idx < count:
                        time.sleep(STAGGER_DELAY)

                for future in as_completed(futures):
                    if self.pixverse_stop_requested:
                        for f in futures:
                            f.cancel()
                        break
                    try:
                        future.result()
                    except Exception:
                        pass
        except Exception as e:
            if not self.pixverse_stop_requested:
                self._pixverse_log(f"Error: {e}")
        finally:
            self.pixverse_running = False
            self._safe_ui(self._pixverse_finish)

    def _pixverse_update_progress(self, step, count):
        self.pixverse_success_lbl.configure(text=str(self.pixverse_success_count))
        self.pixverse_fail_lbl.configure(text=str(self.pixverse_fail_count))
        pct = step / count if count else 0
        self.pixverse_progress_bar.set(pct)
        self.pixverse_progress_pct.configure(text=f"{int(pct * 100)}%")


    def _pixverse_finish(self):
        self.pixverse_start_btn.configure(state="normal")

        if self.pixverse_stop_requested:
            self._set_status("STOPPED")
            msg = (
                f"Proses dihentikan.\n\n"
                f"Selesai: {self.pixverse_success_count + self.pixverse_fail_count}/{self.pixverse_total_count}\n"
                f"Berhasil: {self.pixverse_success_count} -- Gagal: {self.pixverse_fail_count}"
            )
        else:
            self.pixverse_stop_btn.configure(state="normal")
            self._set_status("DONE")
            msg = (
                f"Proses selesai.\n\n"
                f"Berhasil: {self.pixverse_success_count}/{self.pixverse_total_count}\n"
                f"Gagal: {self.pixverse_fail_count}/{self.pixverse_total_count}\n\n"
                f"Browser tetap terbuka. Klik HENTIKAN PROSES untuk menutup semua browser."
            )

        self._pixverse_append_log("Selesai.")
        messagebox.showinfo("PixVerse Creator", msg)

    def _pixverse_register_driver(self, driver):
        with self.pixverse_driver_lock:
            if driver not in self.pixverse_drivers:
                self.pixverse_drivers.append(driver)

    def _pixverse_force_stop_browsers(self):
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

    def update_prompt_inputs(self):
        pass

    def refresh_account_labels(self):
        pass

    def start_video_generate(self):
        if self.gen_running:
            self._pixverse_append_log("Generate sudah berjalan...")
            return

        account_prompts = {}
        try:
            raw = self.prompt_textbox.get("1.0", "end-1c").strip()
        except Exception:
            raw = ""
        all_prompts = [p.strip() for p in re.split(r'\n\s*\n', raw) if p.strip()]

        if not all_prompts:
            messagebox.showwarning(
                "Generate Video",
                "Masukkan minimal satu prompt video terlebih dahulu."
            )
            return

        # distribute prompts round-robin to alive accounts
        with self.pixverse_accounts_lock:
            accounts_copy = sorted(self.pixverse_accounts, key=lambda x: x["index"])
        if not accounts_copy:
            messagebox.showwarning(
                "Generate Video",
                "Tidak ada akun yang tersedia.\\nBuat akun terlebih dahulu sebelum generate video."
            )
            return

        alive = []
        for acc in accounts_copy:
            try:
                _ = acc["driver"].current_url
                alive.append(acc)
            except Exception:
                self._pixverse_append_log(f"[Akun {acc['index']}] Browser tertutup, skip.")

        if not alive:
            messagebox.showwarning(
                "Generate Video",
                "Semua browser sudah tertutup.\nTidak bisa generate video tanpa sesi aktif."
            )
            return

        # --- distribute prompts round-robin ---
        account_prompts = {}
        for i, acc in enumerate(alive):
            idx = acc["index"]
            account_prompts[idx] = all_prompts[i::len(alive)]

        total_videos = len(all_prompts)
        self.gen_running  = True
        self.gen_stop_req = False
        self.gen_total    = total_videos
        self.gen_done     = 0

        self.gen_start_btn.configure(state="disabled")
        self.gen_stop_btn.configure(state="normal")
        self._set_status("RUNNING")
        self._pixverse_append_log(
            f"Mulai generate {total_videos} video dari {len(alive)} akun ({len(alive)} akun, {len(all_prompts)} prompt)..."
        )
        self.pixverse_progress_bar.set(0)
        self.pixverse_progress_pct.configure(text="0%")

        threading.Thread(
            target=self._video_generate_worker,
            args=(alive, account_prompts),
            daemon=True,
        ).start()

    def stop_video_generate(self):
        self.gen_stop_btn.configure(state="disabled")
        if self.gen_running:
            self.gen_stop_req = True
            self._set_status("STOPPING")
            self._pixverse_append_log("Menghentikan generate video...")

    def _video_generate_worker(self, accounts, account_prompts):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        gen_lock = threading.Lock()

        def account_task(acc):
            idx   = acc["index"]
            driver = acc["driver"]
            email  = acc.get("email", "?")

            self._pixverse_log(f"[Akun {idx}] Mulai generate video ({email})...")

            generator = PixVerseVideoGenerator(
                driver,
                log_callback=self._pixverse_log,
                stop_check=lambda: self.gen_stop_req,
            )

            prompts = account_prompts.get(idx, ["", "", ""])
            for vid_num, prompt in enumerate(prompts, start=1):
                if self.gen_stop_req:
                    break

                if not prompt.strip():
                    self._pixverse_log(f"[Akun {idx}] Prompt {vid_num} kosong, skip.")
                    with gen_lock:
                        self.gen_done += 1
                    self._safe_ui(self._gen_update_progress)
                    continue

                self._pixverse_log(
                    f"[Akun {idx}] Video {vid_num}/3 -> "
                    f"{prompt[:50]}{'...' if len(prompt) > 50 else ''}"
                )

                ok = generator.generate_video(
                    prompt_text=prompt,
                    wait_seconds=3,
                    max_concurrent_retries=3,
                    concurrent_wait=45,
                )

                with gen_lock:
                    self.gen_done += 1
                status = "Sukses" if ok else "Gagal"
                self._pixverse_log(f"[Akun {idx}] Video {vid_num}/3 {status}")
                self._safe_ui(self._gen_update_progress)

                if vid_num < len(prompts) and not self.gen_stop_req:
                    time.sleep(5)

        try:
            with ThreadPoolExecutor(max_workers=len(accounts)) as executor:
                futures = {executor.submit(account_task, acc): acc["index"] for acc in accounts}
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        future.result()
                        self._pixverse_log(f"[Akun {idx}] Semua video selesai diproses.")
                    except Exception as e:
                        self._pixverse_log(f"[Akun {idx}] Error: {e}")
        except Exception as e:
            self._pixverse_log(f"Generate worker error: {e}")
        finally:
            self.gen_running = False
            self._safe_ui(self._gen_finish)

    def _gen_update_progress(self):
        pct = self.gen_done / self.gen_total if self.gen_total else 0
        self.pixverse_progress_bar.set(pct)
        self.pixverse_progress_pct.configure(
            text=f"{int(pct * 100)}% ({self.gen_done}/{self.gen_total} video)"
        )

    def _gen_finish(self):
        self.gen_start_btn.configure(state="normal")
        self.gen_stop_btn.configure(state="disabled")
        if self.gen_stop_req:
            self._set_status("STOPPED")
            self._pixverse_append_log("Generate video dihentikan.")
        else:
            self._set_status("DONE")
            self._pixverse_append_log(
                f"Generate selesai! {self.gen_done}/{self.gen_total} video diproses."
            )
            messagebox.showinfo(
                "Generate Video",
                f"Generate video selesai!\n\n"
                f"Total video diproses: {self.gen_done}/{self.gen_total}\n\n"
                f"Gunakan DOWNLOAD SEMUA untuk mengunduh hasilnya."
            )

    def pick_download_folder(self):
        folder = filedialog.askdirectory(
            title="Pilih Folder untuk Menyimpan Video",
            initialdir=self.download_folder,
        )
        if folder:
            self.download_folder = folder
            self.folder_path_label.configure(text=self._truncate_path(folder))
            self._pixverse_append_log(f"Folder download: {folder}")

    def start_video_download(self):
        if self.download_running:
            self._pixverse_append_log("Download sedang berjalan...")
            return

        with self.pixverse_accounts_lock:
            accounts_copy = sorted(self.pixverse_accounts, key=lambda x: x["index"])

        if not accounts_copy:
            messagebox.showwarning(
                "Download Video",
                "Tidak ada akun yang berhasil dibuat.\n"
                "Buat akun terlebih dahulu sebelum download video."
            )
            return

        if not self.download_folder:
            messagebox.showwarning("Download Video", "Pilih folder download terlebih dahulu.")
            return

        alive_accounts = []
        for acc in accounts_copy:
            try:
                _ = acc["driver"].current_url
                alive_accounts.append(acc)
            except Exception:
                self._pixverse_append_log(f"[Akun {acc['index']}] Browser sudah tertutup, skip.")

        if not alive_accounts:
            messagebox.showwarning(
                "Download Video",
                "Semua browser sudah tertutup.\n"
                "Tidak bisa download video tanpa session yang aktif."
            )
            return

        self.download_running        = True
        self.download_stop_requested = False
        self.download_all_btn.configure(state="disabled", text="DOWNLOADING...")
        self._set_status("DOWNLOADING")
        self._pixverse_append_log(f"Mulai download video dari {len(alive_accounts)} akun...")

        threading.Thread(
            target=self._video_download_worker,
            args=(alive_accounts,),
            daemon=True,
        ).start()

    def _video_download_worker(self, accounts):
        try:
            downloader = PixVerseVideoDownloader(
                log_callback=self._pixverse_log,
                stop_check=lambda: self.download_stop_requested,
            )
            success, fail = downloader.download_all(accounts, self.download_folder)

            def finish():
                self.download_running = False
                self.download_all_btn.configure(state="normal", text="DOWNLOAD SEMUA VIDEO")
                self._set_status("RUNNING" if self.pixverse_running else "DONE")
                messagebox.showinfo(
                    "Download Video",
                    f"Download selesai!\n\nBerhasil: {success}\nGagal: {fail}\n\nFolder: {self.download_folder}"
                )

            self._safe_ui(finish)

        except Exception as e:
            def on_error():
                self.download_running = False
                self.download_all_btn.configure(state="normal", text="DOWNLOAD SEMUA VIDEO")
                self._set_status("DONE")
                self._pixverse_append_log(f"Download error: {e}")

            self._safe_ui(on_error)


if __name__ == "__main__":
    app = App()
    app.window.mainloop()
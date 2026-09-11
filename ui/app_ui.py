from datetime import datetime
import math
import os
from tkinter import filedialog
import customtkinter as ctk
import tksvg

from config import resource_path
from core.pipeline import parse_prompts
from ui.theme import (
    ACCENT_BLUE,
    BG_COLOR,
    BORDER_COLOR,
    CARD_BG,
    FONT_MAIN,
    FONT_MONO,
    GREEN_COLOR,
    PURPLE_COLOR,
    PURPLE_HOVER,
    RED_COLOR,
    RED_HOVER,
    TEXT_MAIN,
    TEXT_MUTED,
    WARNING_COLOR,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AppUI:
    """Unified Single-Page Dashboard for AutoPix (Input -> Auto Accounts -> Render -> Download)."""

    def __init__(
        self,
        window: ctk.CTk,
        app_name: str,
        app_version: str,
        status_var: ctk.StringVar,
        default_folder: str,
        on_start,
        on_stop,
    ):
        self.window = window
        self.window.title(f"{app_name} | {app_version}")
        self.window.geometry("1180x760")
        self.window.minsize(980, 640)
        self.window.configure(fg_color=BG_COLOR)

        try:
            self.window.iconbitmap(resource_path("ai.ico"))
        except Exception:
            pass

        self.status_var = status_var
        self.download_folder = default_folder
        self.on_start = on_start
        self.on_stop = on_stop

        self._build_header(app_name, app_version)
        self._build_stats_row()
        self._build_main_workspace()
        self._tick_clock()

    def _tick_clock(self):
        self.clock_label.configure(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.window.after(1000, self._tick_clock)

    def log(self, message: str):
        """Append entry to activity monitor log."""
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{ts}] {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def set_status(self, text: str):
        self.status_var.set(text)
        color_map = {
            "STANDBY": ACCENT_BLUE,
            "RUNNING": WARNING_COLOR,
            "STOPPING": RED_COLOR,
            "STOPPED": "#991B1B",
            "DONE": GREEN_COLOR,
            "DOWNLOADING": PURPLE_COLOR,
        }
        self.status_badge.configure(fg_color=color_map.get(text, ACCENT_BLUE))

    def _build_header(self, app_name: str, app_version: str):
        self.window.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self.window, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 16))
        header.grid_columnconfigure(1, weight=1)

        # Brand box
        brand_frame = ctk.CTkFrame(header, fg_color="transparent")
        brand_frame.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            brand_frame,
            text=f"🎬 {app_name.upper()}",
            font=ctk.CTkFont(family=FONT_MAIN, size=22, weight="bold"),
            text_color=TEXT_MAIN,
        ).pack(side="left")

        ctk.CTkLabel(
            brand_frame,
            text=f" {app_version}",
            font=ctk.CTkFont(family=FONT_MAIN, size=12, weight="bold"),
            text_color=PURPLE_COLOR,
        ).pack(side="left", padx=(4, 0), pady=(4, 0))

        # Right side: Status Badge + Clock
        right_header = ctk.CTkFrame(header, fg_color="transparent")
        right_header.grid(row=0, column=1, sticky="e")

        self.status_badge = ctk.CTkLabel(
            right_header,
            textvariable=self.status_var,
            font=ctk.CTkFont(family=FONT_MAIN, size=11, weight="bold"),
            text_color="#FFFFFF",
            fg_color=ACCENT_BLUE,
            corner_radius=6,
            height=28,
            padx=14,
        )
        self.status_badge.pack(side="left", padx=(0, 14))

        self.clock_label = ctk.CTkLabel(
            right_header,
            text="",
            font=ctk.CTkFont(family=FONT_MONO, size=13, weight="bold"),
            text_color=TEXT_MUTED,
        )
        self.clock_label.pack(side="left")

    def _build_stats_row(self):
        stats_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        stats_frame.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 18))
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.stat_prompts = self._build_stat_card(stats_frame, 0, "PROMPT TERDETEKSI", "0", TEXT_MAIN)
        self.stat_accounts = self._build_stat_card(stats_frame, 1, "AKUN DIBUTUHKAN", "0", PURPLE_COLOR)
        self.stat_accounts_done = self._build_stat_card(stats_frame, 2, "AKUN SELESAI", "0", ACCENT_BLUE)
        self.stat_videos_done = self._build_stat_card(stats_frame, 3, "VIDEO DIUNDUH", "0", GREEN_COLOR)

    def _build_stat_card(self, parent, col: int, title: str, value: str, color: str):
        card = ctk.CTkFrame(
            parent,
            fg_color=CARD_BG,
            corner_radius=12,
            border_color=BORDER_COLOR,
            border_width=1,
        )
        card.grid(row=0, column=col, sticky="ew", padx=4)

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(family=FONT_MAIN, size=11, weight="bold"),
            text_color=TEXT_MUTED,
        ).pack(pady=(12, 2))

        lbl = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(family=FONT_MONO, size=26, weight="bold"),
            text_color=color,
        )
        lbl.pack(pady=(0, 12))
        return lbl

    def _build_main_workspace(self):
        self.window.grid_rowconfigure(2, weight=1)

        workspace = ctk.CTkFrame(self.window, fg_color="transparent")
        workspace.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 24))
        workspace.grid_columnconfigure(0, weight=5)  # Input Prompt & Config (50%)
        workspace.grid_columnconfigure(1, weight=5)  # Log Monitor (50%)
        workspace.grid_rowconfigure(0, weight=1)

        # ── LEFT PANEL: PROMPT INPUT & CONTROL ──
        left_panel = ctk.CTkFrame(
            workspace,
            fg_color=CARD_BG,
            corner_radius=16,
            border_color=BORDER_COLOR,
            border_width=1,
        )
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_panel.grid_columnconfigure(0, weight=1)
        left_panel.grid_rowconfigure(1, weight=1)

        # Panel Header
        left_hdr = ctk.CTkFrame(left_panel, fg_color="transparent")
        left_hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 8))
        left_hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            left_hdr,
            text="Daftar Prompt Video",
            font=ctk.CTkFont(family=FONT_MAIN, size=13, weight="bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, sticky="w")

        self.prompt_calc_lbl = ctk.CTkLabel(
            left_hdr,
            text="0 prompt (0 akun)",
            font=ctk.CTkFont(family=FONT_MAIN, size=11, weight="bold"),
            text_color=PURPLE_COLOR,
        )
        self.prompt_calc_lbl.grid(row=0, column=1, sticky="e")

        # Textarea
        self.prompt_box = ctk.CTkTextbox(
            left_panel,
            fg_color=BG_COLOR,
            border_color=BORDER_COLOR,
            border_width=1,
            text_color=TEXT_MAIN,
            corner_radius=10,
            font=ctk.CTkFont(family=FONT_MAIN, size=12),
        )
        self.prompt_box.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 14))
        self.prompt_box.insert(
            "1.0",
            "Drone shot kota futuristik saat matahari terbenam\n\n"
            "Close-up tangan robotik menyentuh tangan manusia\n\n"
            "Eksplorasi terumbu karang bercahaya di dasar laut",
        )
        self.prompt_box.bind("<KeyRelease>", self._on_prompt_type)

        # Folder row
        folder_row = ctk.CTkFrame(left_panel, fg_color="transparent")
        folder_row.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 16))
        folder_row.grid_columnconfigure(0, weight=1)

        self.folder_lbl = ctk.CTkLabel(
            folder_row,
            text=f"📁 Folder: {self._truncate_path(self.download_folder)}",
            font=ctk.CTkFont(family=FONT_MONO, size=11),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.folder_lbl.grid(row=0, column=0, sticky="w")

        pick_btn = ctk.CTkButton(
            folder_row,
            text="Pilih Folder",
            command=self._pick_folder,
            width=90,
            height=28,
            corner_radius=6,
            fg_color="#222226",
            hover_color="#2d2d33",
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(family=FONT_MAIN, size=11, weight="bold"),
        )
        pick_btn.grid(row=0, column=1, sticky="e")

        # Action Buttons (Mulai & Berhenti)
        action_row = ctk.CTkFrame(left_panel, fg_color="transparent")
        action_row.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        action_row.grid_columnconfigure((0, 1), weight=1)

        self.start_btn = ctk.CTkButton(
            action_row,
            text="🚀 MULAI PROSES OTOMATIS",
            command=self.on_start,
            fg_color=PURPLE_COLOR,
            hover_color=PURPLE_HOVER,
            text_color="#FFFFFF",
            height=46,
            corner_radius=10,
            font=ctk.CTkFont(family=FONT_MAIN, size=13, weight="bold"),
        )
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.stop_btn = ctk.CTkButton(
            action_row,
            text="BERHENTI",
            command=self.on_stop,
            fg_color=RED_COLOR,
            hover_color=RED_HOVER,
            text_color="#FFFFFF",
            height=46,
            corner_radius=10,
            state="disabled",
            font=ctk.CTkFont(family=FONT_MAIN, size=13, weight="bold"),
        )
        self.stop_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # ── RIGHT PANEL: LOG & MONITOR ──
        right_panel = ctk.CTkFrame(
            workspace,
            fg_color=CARD_BG,
            corner_radius=16,
            border_color=BORDER_COLOR,
            border_width=1,
        )
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(2, weight=1)

        right_hdr = ctk.CTkFrame(right_panel, fg_color="transparent")
        right_hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 8))
        right_hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            right_hdr,
            text="Log Aktivitas & Monitor",
            font=ctk.CTkFont(family=FONT_MAIN, size=13, weight="bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, sticky="w")

        self.progress_pct = ctk.CTkLabel(
            right_hdr,
            text="0%",
            font=ctk.CTkFont(family=FONT_MONO, size=13, weight="bold"),
            text_color=PURPLE_COLOR,
        )
        self.progress_pct.grid(row=0, column=1, sticky="e")

        self.progress_bar = ctk.CTkProgressBar(
            right_panel,
            progress_color=PURPLE_COLOR,
            fg_color=BG_COLOR,
            height=10,
            corner_radius=5,
        )
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))

        self.log_box = ctk.CTkTextbox(
            right_panel,
            fg_color=BG_COLOR,
            text_color="#E4E4E7",
            border_color=BORDER_COLOR,
            border_width=1,
            font=ctk.CTkFont(family=FONT_MONO, size=12),
            wrap="word",
            corner_radius=12,
        )
        self.log_box.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.log_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] Sistem AutoPix Siap.\n")
        self.log_box.configure(state="disabled")

        # Initial prompt calc update
        self._on_prompt_type(None)

    def _on_prompt_type(self, event):
        raw = self.prompt_box.get("1.0", "end-1c")
        prompts = parse_prompts(raw)
        n = len(prompts)
        accs = math.ceil(n / 3) if n > 0 else 0
        self.prompt_calc_lbl.configure(text=f"{n} prompt ({accs} akun)")
        self.stat_prompts.configure(text=str(n))
        self.stat_accounts.configure(text=str(accs))

    def _pick_folder(self):
        folder = filedialog.askdirectory(
            title="Pilih Folder Penyimpanan Video",
            initialdir=self.download_folder,
        )
        if folder:
            self.download_folder = folder
            self.folder_lbl.configure(text=f"📁 Folder: {self._truncate_path(folder)}")
            self.log(f"Folder penyimpanan diubah: {folder}")

    @staticmethod
    def _truncate_path(path: str, max_len: int = 40) -> str:
        if len(path) <= max_len:
            return path
        parts = path.replace("\\", "/").split("/")
        if len(parts) <= 2:
            return path
        return parts[0] + "/.../" + "/".join(parts[-2:])

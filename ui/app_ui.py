from datetime import datetime
import os
import customtkinter as ctk
import tksvg

from config import resource_path
from ui.tab_account import TabAccount
from ui.tab_download import TabDownload
from ui.tab_generate import TabGenerate
from ui.theme import (
    ACCENT_BLUE,
    BG_COLOR,
    BORDER_COLOR,
    CARD_BG,
    FONT_MAIN,
    FONT_MONO,
    GREEN_COLOR,
    PURPLE_COLOR,
    RED_COLOR,
    TEXT_MAIN,
    TEXT_MUTED,
    WARNING_COLOR,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AppUI:
    """Master UI Layout for AutoPix (Sidebar Navigation + Switchable Tabs + Live Monitor)."""

    def __init__(
        self,
        window: ctk.CTk,
        app_name: str,
        app_version: str,
        count_var: ctk.StringVar,
        status_var: ctk.StringVar,
        default_folder: str,
        callbacks: dict,
    ):
        self.window = window
        self.window.title(f"{app_name} | {app_version}")
        self.window.geometry("1100x720")
        self.window.minsize(950, 620)
        self.window.configure(fg_color=BG_COLOR)

        try:
            self.window.iconbitmap(resource_path("ai.ico"))
        except Exception:
            pass

        self.status_var = status_var
        self.current_tab = "akun"

        self._build_sidebar(app_name, app_version)
        self._build_main_content(count_var, default_folder, callbacks)
        self._build_monitor()
        self._tick_clock()

        self.select_tab("akun")

    def _tick_clock(self):
        self.clock_label.configure(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.window.after(1000, self._tick_clock)

    def log(self, message: str):
        """Thread-safe append to the activity monitor log."""
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

    def _build_sidebar(self, app_name: str, app_version: str):
        self.window.grid_columnconfigure(1, weight=1)
        self.window.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self.window, fg_color=CARD_BG, corner_radius=0, width=220)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(
            sidebar,
            text=app_name.upper(),
            font=ctk.CTkFont(family=FONT_MAIN, size=20, weight="bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, padx=20, pady=(24, 2), sticky="w")

        ctk.CTkLabel(
            sidebar,
            text=f"{app_version}",
            font=ctk.CTkFont(family=FONT_MAIN, size=12, weight="bold"),
            text_color=PURPLE_COLOR,
        ).grid(row=1, column=0, padx=20, pady=(0, 32), sticky="w")

        # Load SVG Icons
        try:
            self.svg_user = tksvg.SvgImage(file=resource_path("assets/user.svg"), scaletowidth=18)
        except Exception:
            self.svg_user = None

        try:
            self.svg_video = tksvg.SvgImage(file=resource_path("assets/video.svg"), scaletowidth=18)
        except Exception:
            self.svg_video = None

        try:
            self.svg_dl = tksvg.SvgImage(file=resource_path("assets/download.svg"), scaletowidth=18)
        except Exception:
            self.svg_dl = None

        btn_font = ctk.CTkFont(family=FONT_MAIN, size=13, weight="bold")

        self.btn_akun = ctk.CTkButton(
            sidebar,
            text="  Buat Akun",
            image=self.svg_user,
            anchor="w",
            fg_color="transparent",
            text_color=TEXT_MUTED,
            hover_color="#222226",
            command=lambda: self.select_tab("akun"),
            font=btn_font,
            height=40,
        )
        self.btn_akun.grid(row=2, column=0, sticky="ew", padx=12, pady=4)

        self.btn_gen = ctk.CTkButton(
            sidebar,
            text="  Generate Video",
            image=self.svg_video,
            anchor="w",
            fg_color="transparent",
            text_color=TEXT_MUTED,
            hover_color="#222226",
            command=lambda: self.select_tab("gen"),
            font=btn_font,
            height=40,
        )
        self.btn_gen.grid(row=3, column=0, sticky="ew", padx=12, pady=4)

        self.btn_dl = ctk.CTkButton(
            sidebar,
            text="  Download",
            image=self.svg_dl,
            anchor="w",
            fg_color="transparent",
            text_color=TEXT_MUTED,
            hover_color="#222226",
            command=lambda: self.select_tab("dl"),
            font=btn_font,
            height=40,
        )
        self.btn_dl.grid(row=4, column=0, sticky="ew", padx=12, pady=4)

        self.status_badge = ctk.CTkLabel(
            sidebar,
            textvariable=self.status_var,
            font=ctk.CTkFont(family=FONT_MAIN, size=11, weight="bold"),
            text_color="#FFFFFF",
            fg_color=ACCENT_BLUE,
            corner_radius=6,
            height=28,
        )
        self.status_badge.grid(row=5, column=0, sticky="sw", padx=20, pady=(0, 8))

        self.clock_label = ctk.CTkLabel(
            sidebar,
            text="",
            font=ctk.CTkFont(family=FONT_MONO, size=12),
            text_color=TEXT_MUTED,
        )
        self.clock_label.grid(row=6, column=0, sticky="sw", padx=20, pady=(0, 24))

        self.nav_btns = {
            "akun": self.btn_akun,
            "gen": self.btn_gen,
            "dl": self.btn_dl,
        }

    def _build_main_content(self, count_var: ctk.StringVar, default_folder: str, callbacks: dict):
        self.content_container = ctk.CTkFrame(self.window, fg_color="transparent")
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=24, pady=24)
        self.content_container.grid_columnconfigure(0, weight=4)
        self.content_container.grid_columnconfigure(1, weight=5)
        self.content_container.grid_rowconfigure(0, weight=1)

        self.tab_akun = TabAccount(
            self.content_container,
            count_var=count_var,
            on_start=callbacks["start_account"],
            on_stop=callbacks["stop_account"],
        )

        self.tab_gen = TabGenerate(
            self.content_container,
            on_start_gen=callbacks["start_gen"],
            on_stop_gen=callbacks["stop_gen"],
        )

        self.tab_dl = TabDownload(
            self.content_container,
            default_folder=default_folder,
            on_pick_folder=callbacks["pick_folder"],
            on_start_download=callbacks["start_download"],
        )

        self.tabs = {
            "akun": self.tab_akun,
            "gen": self.tab_gen,
            "dl": self.tab_dl,
        }

    def _build_monitor(self):
        monitor_frame = ctk.CTkFrame(
            self.content_container,
            fg_color=CARD_BG,
            corner_radius=16,
            border_color=BORDER_COLOR,
            border_width=1,
        )
        monitor_frame.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        monitor_frame.grid_columnconfigure(0, weight=1)
        monitor_frame.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(monitor_frame, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 8))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr,
            text="Log Aktivitas",
            font=ctk.CTkFont(family=FONT_MAIN, size=13, weight="bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, sticky="w")

        self.progress_pct = ctk.CTkLabel(
            hdr,
            text="0%",
            font=ctk.CTkFont(family=FONT_MONO, size=13, weight="bold"),
            text_color=PURPLE_COLOR,
        )
        self.progress_pct.grid(row=0, column=1, sticky="e")

        self.progress_bar = ctk.CTkProgressBar(
            monitor_frame,
            progress_color=PURPLE_COLOR,
            fg_color=BG_COLOR,
            height=10,
            corner_radius=5,
        )
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))

        self.log_box = ctk.CTkTextbox(
            monitor_frame,
            fg_color=BG_COLOR,
            text_color="#E4E4E7",
            border_color=BORDER_COLOR,
            border_width=1,
            font=ctk.CTkFont(family=FONT_MONO, size=12),
            wrap="word",
            corner_radius=12,
        )
        self.log_box.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.log_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] Sistem Siap.\n")
        self.log_box.configure(state="disabled")

    def select_tab(self, tab_name: str):
        self.current_tab = tab_name
        for name, frame in self.tabs.items():
            if name == tab_name:
                frame.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
                self.nav_btns[name].configure(fg_color=PURPLE_COLOR, text_color="#FFFFFF")
            else:
                frame.grid_forget()
                self.nav_btns[name].configure(fg_color="transparent", text_color=TEXT_MUTED)

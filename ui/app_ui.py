import os
import tkinter.filedialog as fd
from typing import Callable, Optional

import customtkinter as ctk
from config import APP_NAME, APP_VERSION
from ui.components.glass_card import GlassCard
from ui.components.log_terminal import LogTerminal
from ui.components.prompt_editor import PromptEditor
from ui.components.stats_bar import StatsBar
from ui.theme import (
    BG_COLOR,
    BORDER_GLASS,
    BTN_DANGER_BG,
    BTN_DANGER_BORDER,
    BTN_DANGER_FG,
    BTN_DANGER_HOVER,
    BTN_PRIMARY_BG,
    BTN_PRIMARY_FG,
    BTN_PRIMARY_HOVER,
    FONT_MAIN,
    FONT_MONO,
    STATUS_IDLE_BG,
    STATUS_IDLE_FG,
    STATUS_RUN_BG,
    STATUS_RUN_FG,
    SURFACE_DOCK,
    SURFACE_GLASS,
    SURFACE_INSET,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SECONDARY,
)


class AppUI:
    """
    Main View Layout for AutoPix:
    Dark AMOLED + Translucent Glassmorphism Interface.
    """

    def __init__(
        self,
        window: ctk.CTk,
        default_folder: str,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
    ):
        self.window = window
        self.default_folder = default_folder
        self.on_start = on_start
        self.on_stop = on_stop

        self._init_window()
        self._build_header()
        self._build_stats()
        self._build_workspace()
        self._build_dock()

    def _init_window(self):
        self.window.title(f"{APP_NAME} {APP_VERSION} — AMOLED Glass")
        self.window.geometry("1100, 780")
        self.window.minsize(980, 680)
        self.window.configure(fg_color=BG_COLOR)
        ctk.set_appearance_mode("dark")

    def _build_header(self):
        header_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        header_frame.pack(fill="x", padx=24, pady=(20, 14))

        # Title & Subtitle
        left_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_box.pack(side="left")

        title_lbl = ctk.CTkLabel(
            left_box,
            text=APP_NAME.upper(),
            font=(FONT_MAIN, 22, "bold"),
            text_color=TEXT_MAIN,
        )
        title_lbl.pack(side="left")

        ver_badge = ctk.CTkLabel(
            left_box,
            text=APP_VERSION,
            font=(FONT_MONO, 10, "bold"),
            text_color=TEXT_MUTED,
            fg_color=SURFACE_GLASS,
            corner_radius=6,
            padx=8,
            pady=2,
        )
        ver_badge.pack(side="left", padx=10)

        # Status Badge (Right)
        self.status_chip = ctk.CTkLabel(
            header_frame,
            text="● STANDBY",
            font=(FONT_MONO, 11, "bold"),
            text_color=STATUS_IDLE_FG,
            fg_color=STATUS_IDLE_BG,
            corner_radius=8,
            padx=12,
            pady=4,
        )
        self.status_chip.pack(side="right")

    def _build_stats(self):
        stats_container = ctk.CTkFrame(self.window, fg_color="transparent")
        stats_container.pack(fill="x", padx=24, pady=(0, 14))

        self.stats_bar = StatsBar(stats_container)
        self.stats_bar.pack(fill="x")

    def _build_workspace(self):
        workspace = ctk.CTkFrame(self.window, fg_color="transparent")
        workspace.pack(fill="both", expand=True, padx=24, pady=(0, 14))

        workspace.columnconfigure(0, weight=5, uniform="split")
        workspace.columnconfigure(1, weight=5, uniform="split")
        workspace.rowconfigure(0, weight=1)

        # Left Column: Prompt Editor
        self.prompt_editor = PromptEditor(workspace)
        self.prompt_editor.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Right Column: Log Terminal
        self.log_terminal = LogTerminal(workspace)
        self.log_terminal.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    def _build_dock(self):
        # Bottom Dock Container
        dock_card = GlassCard(
            self.window,
            corner_radius=14,
            fg_color=SURFACE_DOCK,
            border_color=BORDER_GLASS,
        )
        dock_card.pack(fill="x", padx=24, pady=(0, 20))

        inner = ctk.CTkFrame(dock_card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        # Destination Folder Selector
        folder_box = ctk.CTkFrame(inner, fg_color="transparent")
        folder_box.pack(side="left", fill="x", expand=True, padx=(0, 20))

        folder_tag = ctk.CTkLabel(
            folder_box,
            text="SAVE DIRECTORY",
            font=(FONT_MONO, 10, "bold"),
            text_color=TEXT_MUTED,
        )
        folder_tag.pack(anchor="w", pady=(0, 2))

        folder_input_row = ctk.CTkFrame(folder_box, fg_color="transparent")
        folder_input_row.pack(fill="x")

        self.folder_var = ctk.StringVar(value=self.default_folder)
        self.folder_entry = ctk.CTkEntry(
            folder_input_row,
            textvariable=self.folder_var,
            font=(FONT_MONO, 11),
            fg_color=SURFACE_INSET,
            border_color=BORDER_GLASS,
            text_color=TEXT_MAIN,
            height=34,
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = ctk.CTkButton(
            folder_input_row,
            text="Browse",
            font=(FONT_MAIN, 11),
            width=70,
            height=34,
            fg_color=SURFACE_GLASS,
            border_color=BORDER_GLASS,
            border_width=1,
            text_color=TEXT_SECONDARY,
            hover_color=BORDER_GLASS,
            command=self._choose_folder,
        )
        browse_btn.pack(side="right")

        # Action Buttons (Start / Stop)
        action_box = ctk.CTkFrame(inner, fg_color="transparent")
        action_box.pack(side="right")

        self.stop_btn = ctk.CTkButton(
            action_box,
            text="Stop",
            font=(FONT_MAIN, 13, "bold"),
            width=90,
            height=36,
            fg_color=BTN_DANGER_BG,
            border_color=BTN_DANGER_BORDER,
            border_width=1,
            text_color=BTN_DANGER_FG,
            hover_color=BTN_DANGER_HOVER,
            command=self.on_stop,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=(0, 10))

        self.start_btn = ctk.CTkButton(
            action_box,
            text="Start Pipeline",
            font=(FONT_MAIN, 13, "bold"),
            width=130,
            height=36,
            fg_color=BTN_PRIMARY_BG,
            text_color=BTN_PRIMARY_FG,
            hover_color=BTN_PRIMARY_HOVER,
            command=self.on_start,
        )
        self.start_btn.pack(side="right")

    def _choose_folder(self):
        chosen = fd.askdirectory(initialdir=self.folder_var.get())
        if chosen:
            self.folder_var.set(chosen)

    def set_running_state(self, running: bool):
        if running:
            self.status_chip.configure(
                text="● PROCESSING",
                text_color=STATUS_RUN_FG,
                fg_color=STATUS_RUN_BG,
            )
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
        else:
            self.status_chip.configure(
                text="● STANDBY",
                text_color=STATUS_IDLE_FG,
                fg_color=STATUS_IDLE_BG,
            )
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")

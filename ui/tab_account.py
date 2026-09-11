import customtkinter as ctk
from ui.theme import (
    ACCENT_BLUE,
    ACCENT_HOVER,
    BG_COLOR,
    BORDER_COLOR,
    FONT_MAIN,
    FONT_MONO,
    GREEN_COLOR,
    RED_COLOR,
    RED_HOVER,
    TEXT_MAIN,
    TEXT_MUTED,
)


class TabAccount(ctk.CTkFrame):
    """Tab 1: Pengaturan dan pemantauan pembuatan akun PixVerse."""

    def __init__(self, parent, count_var: ctk.StringVar, on_start, on_stop):
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        # 1. Judul Bagian
        ctk.CTkLabel(
            self,
            text="Pengaturan Akun",
            font=ctk.CTkFont(family=FONT_MAIN, size=14, weight="bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, sticky="w", pady=(10, 14))

        # 2. Statistik Kartu (Target, Berhasil, Gagal)
        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.grid(row=1, column=0, sticky="ew", pady=(0, 24))
        stats_row.grid_columnconfigure((0, 1, 2), weight=1)

        self.stat_target = self._build_stat_card(stats_row, 0, "TARGET", "0", TEXT_MAIN)
        self.stat_success = self._build_stat_card(stats_row, 1, "BERHASIL", "0", GREEN_COLOR)
        self.stat_fail = self._build_stat_card(stats_row, 2, "GAGAL", "0", RED_COLOR)

        # 3. Input Jumlah Akun
        ctk.CTkLabel(
            self,
            text="Jumlah Akun",
            font=ctk.CTkFont(family=FONT_MAIN, size=12, weight="bold"),
            text_color=TEXT_MUTED,
        ).grid(row=2, column=0, sticky="w", pady=(0, 6))

        self.count_entry = ctk.CTkEntry(
            self,
            textvariable=count_var,
            fg_color=BG_COLOR,
            border_color=BORDER_COLOR,
            text_color=TEXT_MAIN,
            corner_radius=10,
            height=42,
            font=ctk.CTkFont(family=FONT_MAIN, size=14),
        )
        self.count_entry.grid(row=3, column=0, sticky="ew", pady=(0, 28))

        # 4. Tombol Aksi (Mulai & Berhenti)
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self.start_btn = ctk.CTkButton(
            btn_row,
            text="Mulai",
            command=on_start,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_HOVER,
            text_color="#FFFFFF",
            height=46,
            corner_radius=10,
            font=ctk.CTkFont(family=FONT_MAIN, size=13, weight="bold"),
        )
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.stop_btn = ctk.CTkButton(
            btn_row,
            text="Berhenti",
            command=on_stop,
            fg_color=RED_COLOR,
            hover_color=RED_HOVER,
            text_color="#FFFFFF",
            height=46,
            corner_radius=10,
            state="disabled",
            font=ctk.CTkFont(family=FONT_MAIN, size=13, weight="bold"),
        )
        self.stop_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _build_stat_card(self, parent, col: int, title: str, value: str, color: str):
        card = ctk.CTkFrame(
            parent,
            fg_color=BG_COLOR,
            corner_radius=12,
            border_color=BORDER_COLOR,
            border_width=1,
        )
        pad = (0, 8) if col < 2 else (0, 0)
        card.grid(row=0, column=col, sticky="ew", padx=pad)

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(family=FONT_MAIN, size=11, weight="bold"),
            text_color=TEXT_MUTED,
        ).pack(pady=(12, 2))

        lbl = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(family=FONT_MONO, size=28, weight="bold"),
            text_color=color,
        )
        lbl.pack(pady=(0, 12))
        return lbl

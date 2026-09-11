import customtkinter as ctk
from ui.theme import (
    BG_COLOR,
    BORDER_COLOR,
    FONT_MAIN,
    FONT_MONO,
    PURPLE_COLOR,
    PURPLE_HOVER,
    TEXT_MAIN,
    TEXT_MUTED,
)


class TabDownload(ctk.CTkFrame):
    """Tab 3: Manajemen penyimpanan folder dan eksekusi pengunduhan video."""

    def __init__(self, parent, default_folder: str, on_pick_folder, on_start_download):
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Penyimpanan Video",
            font=ctk.CTkFont(family=FONT_MAIN, size=14, weight="bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, sticky="w", pady=(10, 14))

        card_folder = ctk.CTkFrame(
            self,
            fg_color=BG_COLOR,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        card_folder.grid(row=1, column=0, sticky="ew", pady=(0, 24), padx=2)
        card_folder.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card_folder,
            text="LOKASI FOLDER",
            font=ctk.CTkFont(family=FONT_MAIN, size=11, weight="bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=16, pady=(14, 4))

        self.folder_path_label = ctk.CTkLabel(
            card_folder,
            text=self._truncate_path(default_folder),
            font=ctk.CTkFont(family=FONT_MONO, size=12),
            text_color=TEXT_MAIN,
            wraplength=380,
            justify="left",
        )
        self.folder_path_label.pack(anchor="w", padx=16, pady=(0, 14))

        self.pick_folder_btn = ctk.CTkButton(
            self,
            text="Pilih Folder",
            command=on_pick_folder,
            fg_color="#18181C",
            hover_color="#222226",
            text_color=TEXT_MAIN,
            height=42,
            corner_radius=10,
            border_width=1,
            border_color=BORDER_COLOR,
            font=ctk.CTkFont(family=FONT_MAIN, size=12, weight="bold"),
        )
        self.pick_folder_btn.grid(row=2, column=0, sticky="ew", pady=(0, 24))

        self.download_all_btn = ctk.CTkButton(
            self,
            text="Download",
            command=on_start_download,
            fg_color=PURPLE_COLOR,
            hover_color=PURPLE_HOVER,
            text_color="#FFFFFF",
            height=48,
            corner_radius=10,
            font=ctk.CTkFont(family=FONT_MAIN, size=14, weight="bold"),
        )
        self.download_all_btn.grid(row=3, column=0, sticky="ew")

    @staticmethod
    def _truncate_path(path: str, max_len: int = 40) -> str:
        if len(path) <= max_len:
            return path
        parts = path.replace("\\", "/").split("/")
        if len(parts) <= 2:
            return path
        return parts[0] + "/.../" + "/".join(parts[-2:])

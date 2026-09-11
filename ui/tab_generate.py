import customtkinter as ctk
from ui.theme import (
    BORDER_COLOR,
    CARD_BG,
    FONT_MAIN,
    PURPLE_COLOR,
    PURPLE_HOVER,
    RED_COLOR,
    RED_HOVER,
    TEXT_MAIN,
)


class TabGenerate(ctk.CTkFrame):
    """Tab 2: Input prompt video dan kontrol batch generator."""

    def __init__(self, parent, on_start_gen, on_stop_gen):
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text="Prompt Video",
            font=ctk.CTkFont(family=FONT_MAIN, size=14, weight="bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, sticky="w", pady=(10, 10))

        self.prompt_textbox = ctk.CTkTextbox(
            self,
            fg_color=CARD_BG,
            border_color=BORDER_COLOR,
            text_color=TEXT_MAIN,
            corner_radius=8,
            border_width=1,
            font=ctk.CTkFont(family=FONT_MAIN, size=12),
        )
        self.prompt_textbox.grid(row=1, column=0, sticky="nsew", pady=(0, 20))
        self.prompt_textbox.insert(
            "1.0",
            "Masukkan prompt di sini.\nPisahkan dengan satu baris kosong.\n\n"
            "Contoh prompt 1\n\nContoh prompt 2",
        )

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew")
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self.gen_start_btn = ctk.CTkButton(
            btn_row,
            text="Generate",
            command=on_start_gen,
            fg_color=PURPLE_COLOR,
            hover_color=PURPLE_HOVER,
            text_color="#FFFFFF",
            height=46,
            corner_radius=10,
            font=ctk.CTkFont(family=FONT_MAIN, size=13, weight="bold"),
        )
        self.gen_start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.gen_stop_btn = ctk.CTkButton(
            btn_row,
            text="Berhenti",
            command=on_stop_gen,
            fg_color=RED_COLOR,
            hover_color=RED_HOVER,
            text_color="#FFFFFF",
            height=46,
            corner_radius=10,
            state="disabled",
            font=ctk.CTkFont(family=FONT_MAIN, size=13, weight="bold"),
        )
        self.gen_stop_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

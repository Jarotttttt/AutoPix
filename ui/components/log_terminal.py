import customtkinter as ctk
from ui.components.glass_card import GlassCard
from ui.theme import (
    BORDER_GLASS,
    FONT_MONO,
    SURFACE_INSET,
    TERM_ERROR,
    TERM_INFO,
    TERM_SUCCESS,
    TERM_TEXT,
    TERM_WARN,
    TEXT_MUTED,
    TEXT_SECONDARY,
)


class LogTerminal(ctk.CTkFrame):
    """
    AMOLED Inset Console Box with colored tag syntax and auto-scroll.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        # Header Row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        title = ctk.CTkLabel(
            header,
            text="ACTIVITY STREAM",
            font=(FONT_MONO, 11, "bold"),
            text_color=TEXT_SECONDARY,
        )
        title.pack(side="left")

        clear_btn = ctk.CTkButton(
            header,
            text="CLEAR",
            font=(FONT_MONO, 10),
            width=50,
            height=22,
            fg_color="transparent",
            text_color=TEXT_MUTED,
            hover_color=SURFACE_INSET,
            command=self.clear,
        )
        clear_btn.pack(side="right")

        # Inset Container
        self.well = GlassCard(
            self,
            fg_color=SURFACE_INSET,
            border_color=BORDER_GLASS,
            corner_radius=12,
        )
        self.well.pack(fill="both", expand=True)

        self.textbox = ctk.CTkTextbox(
            self.well,
            fg_color="transparent",
            text_color=TERM_TEXT,
            font=(FONT_MONO, 11),
            wrap="word",
            border_width=0,
        )
        self.textbox.pack(fill="both", expand=True, padx=10, pady=10)

        # Syntax Color Tags
        self.textbox.tag_config("INFO", foreground=TERM_INFO)
        self.textbox.tag_config("SUCCESS", foreground=TERM_SUCCESS)
        self.textbox.tag_config("WARN", foreground=TERM_WARN)
        self.textbox.tag_config("ERROR", foreground=TERM_ERROR)
        self.textbox.tag_config("DEFAULT", foreground=TERM_TEXT)

    def append_log(self, text: str, level: str = "INFO"):
        self.textbox.configure(state="normal")
        tag = level if level in ["INFO", "SUCCESS", "WARN", "ERROR"] else "DEFAULT"
        self.textbox.insert("end", text + "\n", tag)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")

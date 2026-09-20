import customtkinter as ctk
from ui.components.glass_card import GlassCard
from ui.theme import (
    BORDER_FOCUS,
    BORDER_GLASS,
    FONT_MAIN,
    FONT_MONO,
    SURFACE_INSET,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SECONDARY,
)
from utils.helpers import parse_prompts


class PromptEditor(ctk.CTkFrame):
    """
    Recessed dark AMOLED textarea for video prompts with live counter badge.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        # Header Row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        title = ctk.CTkLabel(
            header,
            text="PROMPT QUEUE",
            font=(FONT_MONO, 11, "bold"),
            text_color=TEXT_SECONDARY,
        )
        title.pack(side="left")

        self.count_badge = ctk.CTkLabel(
            header,
            text="0 PROMPTS",
            font=(FONT_MONO, 10, "bold"),
            text_color=TEXT_MUTED,
            fg_color=SURFACE_INSET,
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.count_badge.pack(side="right")

        # Inset Well Container
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
            text_color=TEXT_MAIN,
            font=(FONT_MAIN, 13),
            undo=True,
            wrap="word",
            border_width=0,
        )
        self.textbox.pack(fill="both", expand=True, padx=10, pady=10)

        self.textbox.bind("<KeyRelease>", self._on_text_change)

    def _on_text_change(self, event=None):
        raw = self.textbox.get("1.0", "end-1c")
        prompts = parse_prompts(raw)
        cnt = len(prompts)
        label = f"{cnt} PROMPT{'S' if cnt != 1 else ''}"
        self.count_badge.configure(text=label)

    def get_prompts(self):
        raw = self.textbox.get("1.0", "end-1c")
        return parse_prompts(raw)

    def get_raw_text(self):
        return self.textbox.get("1.0", "end-1c")

    def clear(self):
        self.textbox.delete("1.0", "end")
        self._on_text_change()

import customtkinter as ctk
from ui.components.glass_card import GlassCard
from ui.theme import BORDER_GLASS, FONT_MAIN, FONT_MONO, TEXT_MAIN, TEXT_MUTED, TEXT_SECONDARY


class StatsBar(ctk.CTkFrame):
    """
    AMOLED Glass stat chips showing Accounts created, Videos Generated, and Downloaded.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.columnconfigure((0, 1, 2), weight=1, uniform="stats")

        # 1. Accounts Chip
        self.accounts_card, self.accounts_val = self._create_chip(
            col=0,
            label="ACCOUNTS",
            icon="👤",
            initial_val="0",
        )

        # 2. Generated Chip
        self.generated_card, self.generated_val = self._create_chip(
            col=1,
            label="GENERATED",
            icon="🎬",
            initial_val="0",
        )

        # 3. Downloaded Chip
        self.downloaded_card, self.downloaded_val = self._create_chip(
            col=2,
            label="DOWNLOADED",
            icon="📥",
            initial_val="0",
        )

    def _create_chip(self, col: int, label: str, icon: str, initial_val: str):
        card = GlassCard(self, corner_radius=12)
        card.grid(row=0, column=col, padx=5, pady=0, sticky="ew")

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(padx=14, pady=10, fill="both", expand=True)

        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x", anchor="w")

        icon_lbl = ctk.CTkLabel(
            header,
            text=icon,
            font=(FONT_MAIN, 13),
            text_color=TEXT_MUTED,
        )
        icon_lbl.pack(side="left", padx=(0, 6))

        tag_lbl = ctk.CTkLabel(
            header,
            text=label,
            font=(FONT_MONO, 10, "bold"),
            text_color=TEXT_TERTIARY if 'TEXT_TERTIARY' in globals() else TEXT_MUTED,
        )
        tag_lbl.pack(side="left")

        val_lbl = ctk.CTkLabel(
            content,
            text=initial_val,
            font=(FONT_MAIN, 22, "bold"),
            text_color=TEXT_MAIN,
        )
        val_lbl.pack(anchor="w", pady=(2, 0))

        return card, val_lbl

    def update_stats(self, accounts: int, generated: int, downloaded: int):
        self.accounts_val.configure(text=str(accounts))
        self.generated_val.configure(text=str(generated))
        self.downloaded_val.configure(text=str(downloaded))

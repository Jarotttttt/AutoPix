from typing import Optional

import customtkinter as ctk
from ui.theme import BORDER_GLASS, SURFACE_GLASS


class GlassCard(ctk.CTkFrame):
    """
    Frosted dark glass card container with subtle hairline specular border.
    """

    def __init__(
        self,
        master,
        corner_radius: int = 14,
        border_width: int = 1,
        fg_color: str = SURFACE_GLASS,
        border_color: str = BORDER_GLASS,
        **kwargs,
    ):
        super().__init__(
            master=master,
            corner_radius=corner_radius,
            border_width=border_width,
            fg_color=fg_color,
            border_color=border_color,
            **kwargs,
        )

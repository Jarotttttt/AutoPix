import os
import re

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add tksvg import
if 'import tksvg' not in content:
    content = content.replace('import customtkinter as ctk', 'import customtkinter as ctk\nimport tksvg')

# Replace _build_ui completely
new_ui = '''    def _build_ui(self):
        self.window.grid_columnconfigure(1, weight=1)
        self.window.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        sidebar = ctk.CTkFrame(self.window, fg_color=CARD_BG, corner_radius=0, width=220)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_rowconfigure(5, weight=1)
        
        brand_lbl = ctk.CTkLabel(sidebar, text=APP_NAME.upper(), font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        brand_lbl.grid(row=0, column=0, padx=20, pady=(24, 2), sticky="w")
        version_lbl = ctk.CTkLabel(sidebar, text=f"{APP_VERSION}", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=PURPLE_COLOR)
        version_lbl.grid(row=1, column=0, padx=20, pady=(0, 32), sticky="w")
        
        self.svg_user = tksvg.SvgImage(file="assets/user.svg", scaletowidth=18)
        self.svg_video = tksvg.SvgImage(file="assets/video.svg", scaletowidth=18)
        self.svg_dl = tksvg.SvgImage(file="assets/download.svg", scaletowidth=18)

        btn_font = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        self.btn_akun = ctk.CTkButton(sidebar, text="  Buat Akun", image=self.svg_user, anchor="w", fg_color="transparent", text_color=TEXT_MUTED, hover_color="#222226", command=lambda: self.select_tab("akun"), font=btn_font, height=40)
        self.btn_akun.grid(row=2, column=0, sticky="ew", padx=12, pady=4)
        
        self.btn_gen = ctk.CTkButton(sidebar, text="  Generate Video", image=self.svg_video, anchor="w", fg_color="transparent", text_color=TEXT_MUTED, hover_color="#222226", command=lambda: self.select_tab("gen"), font=btn_font, height=40)
        self.btn_gen.grid(row=3, column=0, sticky="ew", padx=12, pady=4)
        
        self.btn_dl = ctk.CTkButton(sidebar, text="  Download", image=self.svg_dl, anchor="w", fg_color="transparent", text_color=TEXT_MUTED, hover_color="#222226", command=lambda: self.select_tab("dl"), font=btn_font, height=40)
        self.btn_dl.grid(row=4, column=0, sticky="ew", padx=12, pady=4)
        
        # Status & Clock at bottom
        self.status_badge = ctk.CTkLabel(sidebar, textvariable=self.status_var, font=ctk.CTkFont(size=11, weight="bold"), text_color="#FFF", fg_color=ACCENT_BLUE, corner_radius=6, height=28)
        self.status_badge.grid(row=5, column=0, sticky="sw", padx=20, pady=(0, 8))
        
        self.clock_label = ctk.CTkLabel(sidebar, text="", font=ctk.CTkFont(family="Consolas", size=12), text_color=TEXT_MUTED)
        self.clock_label.grid(row=6, column=0, sticky="sw", padx=20, pady=(0, 24))
        
        # --- Main Content ---
        main_content = ctk.CTkFrame(self.window, fg_color="transparent")
        main_content.grid(row=0, column=1, sticky="nsew", padx=24, pady=24)
        main_content.grid_columnconfigure(0, weight=4)
        main_content.grid_columnconfigure(1, weight=5)
        main_content.grid_rowconfigure(0, weight=1)
        
        self.frame_akun = ctk.CTkFrame(main_content, fg_color="transparent")
        self.frame_gen = ctk.CTkFrame(main_content, fg_color="transparent")
        self.frame_dl = ctk.CTkFrame(main_content, fg_color="transparent")
        
        self._build_tab_akun(self.frame_akun)
        self._build_tab_generate(self.frame_gen)
        self._build_tab_download(self.frame_dl)
        
        self.frames = {"akun": self.frame_akun, "gen": self.frame_gen, "dl": self.frame_dl}
        self.btns = {"akun": self.btn_akun, "gen": self.btn_gen, "dl": self.btn_dl}
        
        self._build_monitor(main_content)
        
        self.select_tab("akun")

    def select_tab(self, tab_name):
        for name, frame in self.frames.items():
            if name == tab_name:
                frame.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
                self.btns[name].configure(fg_color=PURPLE_COLOR, text_color="#FFF")
            else:
                frame.grid_forget()
                self.btns[name].configure(fg_color="transparent", text_color=TEXT_MUTED)

    def _build_tab_akun'''

pattern = r'    def _build_ui\(self\):.*?    def _build_tab_akun'
content = re.sub(pattern, new_ui, content, flags=re.DOTALL)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

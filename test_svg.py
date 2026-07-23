import customtkinter as ctk
import tksvg

app = ctk.CTk()
try:
    svg_image = tksvg.SvgImage(file='assets/user.svg', scaletowidth=24)
    btn = ctk.CTkButton(app, text='Test', image=svg_image)
    btn.pack()
    print('SUCCESS')
except Exception as e:
    print('FAIL:', e)
app.update()
app.destroy()

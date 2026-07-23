# 🚀 AutoPix

<p align="center">
  <img src="https://img.shields.io/badge/versi-3.0-7C3AED?style=flat-square" alt="Versi 3.0"/>
  <img src="https://img.shields.io/badge/python-3.10%2B-2563EB?style=flat-square" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/GUI-CustomTkinter-10B981?style=flat-square" alt="CustomTkinter"/>
  <img src="https://img.shields.io/badge/license-MIT-F59E0B?style=flat-square" alt="License MIT"/>
</p>

<p align="center">
  <b>Alat otomatisasi desktop untuk PixVerse</b> — <br/>
  Buat akun, generate video AI, dan unduh — semua dari sidebar navigasi dengan ikon SVG.
</p>

---

## ✨ Fitur

| Fitur | Deskripsi |
|-------|-----------|
| 🤖 **Buat Akun** | Daftarkan akun PixVerse otomatis via temp-mail.ai + deteksi OTP |
| 🎥 **Generate Video** | Batch-generate video dari teks prompt, round-robin ke semua akun |
| ⬇️ **Download** | Deteksi & download semua video ke folder lokal |
| 🧵 **Paralel** | Semua browser berjalan bersamaan via `ThreadPoolExecutor` |
| 🛡️ **Anti-Deteksi** | SeleniumBase + undetected-chromedriver |
| 🎨 **Sidebar UI** | Navigasi sidebar modern dengan ikon SVG |

---

## 🚀 Mulai Cepat

```bash
pip install customtkinter seleniumbase requests pillow tksvg
python main.py
```

### 🔧 Build Executable

```bash
pip install pyinstaller
pyinstaller main.spec
```

---

## 🧠 Cara Kerja

```
┌─────────────┐    ┌─────────────┐    ┌────────────┐
│  Buat Akun  │───▶│  Generate   │───▶│  Download  │
│             │    │  Video      │    │  Video     │
└─────────────┘    └─────────────┘    └────────────┘
```

1. **Buat Akun** — Buka N browser, daftar via temp-mail.ai, simpan sesi login
2. **Generate** — Distribusi prompt round-robin, handle popup limit otomatis
3. **Download** — Transfer cookie → download video langsung

---

## ⚙️ Format Prompt

Paste prompt di text box, pisahkan dengan **satu baris kosong**:

```
Sebuah drone shot kota futuristik saat matahari terbenam

Close-up tangan robot menyentuh tangan manusia

Eksplorasi bawah laut terumbu karang
```

---

## 📁 Struktur Proyek

```
├── main.py                         # Entry point GUI
├── main.spec                       # PyInstaller config
├── assets/                         # SVG icons untuk sidebar
│   ├── user.svg
│   ├── video.svg
│   └── download.svg
├── core/
│   ├── pixverse_creator.py         # Registrasi akun
│   ├── pixverse_video_generator.py # Generate video
│   └── video_downloader.py         # Download engine
├── .gitignore
└── README.md
```

---

## 🧪 Teknologi

| Teknologi | Kegunaan |
|-----------|----------|
| CustomTkinter | GUI dark modern |
| SeleniumBase | Browser automation anti-deteksi |
| tksvg | Rendering ikon SVG native |
| temp-mail.ai | API email sementara |
| Python 3.10+ | Bahasa utama |

---

## ⚠️ Disclaimer

Untuk **tujuan edukasi**. Gunakan sesuai Ketentuan Layanan PixVerse.

---

<p align="center">
  Dibuat dengan ⚡ oleh <b>Creator La</b>
</p>

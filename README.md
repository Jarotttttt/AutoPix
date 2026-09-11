# 🚀 AutoPix

<p align="center">
  <img src="https://img.shields.io/badge/versi-3.0-7C3AED?style=flat-square" alt="Versi 3.0"/>
  <img src="https://img.shields.io/badge/python-3.10%2B-2563EB?style=flat-square" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/GUI-CustomTkinter-10B981?style=flat-square" alt="CustomTkinter"/>
  <img src="https://img.shields.io/badge/Automation-SeleniumBase-FF5722?style=flat-square" alt="SeleniumBase"/>
  <img src="https://img.shields.io/badge/license-MIT-F59E0B?style=flat-square" alt="License MIT"/>
</p>

<p align="center">
  <b>Alat otomatisasi desktop pintar untuk platform PixVerse</b> — <br/>
  Pembuatan akun massal, batch video generator dari teks prompt, dan unduhan otomatis terpusat.
</p>

---

## ✨ Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| 🤖 **Buat Akun Otomatis** | Daftarkan akun PixVerse otomatis via API temp-mail.ai & polling OTP otomatis |
| 🎥 **Batch Generator Video** | Distribusi prompt video sistem round-robin ke semua browser aktif |
| ⬇️ **Auto-Downloader** | Transfer session cookies browser → unduh semua video hasil render ke folder lokal |
| 🧵 **Multithreading Paralel** | Eksekusi konkuren via `ThreadPoolExecutor` tanpa membuat antarmuka macet (*freeze*) |
| 🛡️ **Anti-Deteksi Bot** | SeleniumBase UC mode (`uc=True`) untuk melewati proteksi otomasi browser |
| 🎨 **Modern Sidebar UI** | Dashboard dark theme modern dengan navigasi sidebar tab dan ikon SVG native |
| 📊 **Live Monitor & Log** | Progress bar, persentase progres, dan pencatatan aktivitas real-time |

---

## 🧠 Alur Kerja

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ 1. Buat Akun    │ ───▶  │ 2. Generate     │ ───▶  │ 3. Download     │
│    (Email + OTP)│       │    (Round-Robin)│       │    (Direct MP4) │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

1. **Buat Akun** — Luncurkan N browser bertahap, daftarkan akun via temp-mail.ai, verifikasi OTP, simpan sesi aktif.
2. **Generate Video** — Masukkan daftar prompt, sistem membaginya rata ke browser yang aktif, menangani switch dan limit antrean secara otomatis.
3. **Download Video** — Ekstrak link video dari halaman dashboard dan unduh langsung secara streaming ke folder pilihan.

---

## 📁 Struktur Proyek

```
AutoPix/
├── assets/                     # Ikon vektor SVG untuk navigasi
│   ├── user.svg
│   ├── video.svg
│   └── download.svg
├── core/                       # Layanan backend & otomasi Selenium
│   ├── __init__.py
│   ├── mail_service.py         # Klien temp-mail.ai & ekstraksi OTP
│   ├── account_creator.py      # Otomasi pendaftaran akun SeleniumBase
│   ├── video_generator.py      # Otomasi pengisian prompt & klik generate
│   └── video_downloader.py     # Ekstraksi media & download via cookie session
├── ui/                         # Komponen antarmuka CustomTkinter
│   ├── __init__.py
│   ├── theme.py                # Palet warna Dark Mode & styling
│   ├── tab_account.py          # Panel tab Buat Akun & kartu statistik
│   ├── tab_generate.py         # Panel tab input prompt video
│   ├── tab_download.py         # Panel tab lokasi folder unduhan
│   └── app_ui.py               # Layout master sidebar & monitor log
├── config.py                   # Konfigurasi aplikasi, endpoint, & konstanta
├── main.py                     # Entry point & thread pool orchestrator
├── AutoPix.spec                # Konfigurasi PyInstaller
├── requirements.txt            # Daftar pustaka dependensi
├── ai.ico                      # Ikon aplikasi
├── LICENSE                     # Lisensi MIT
└── README.md                   # Dokumentasi proyek
```

---

## 🛠️ Prasyarat & Instalasi

### 1. Kebutuhan Sistem
- Python 3.10 atau yang lebih baru (disarankan Python 3.11)
- Google Chrome terpasang di sistem

### 2. Clone Repository
```bash
git clone https://github.com/Jarotttttt/AutoPix.git
cd AutoPix
```

### 3. Pasang Dependensi
```bash
pip install -r requirements.txt
```

### 4. Jalankan Aplikasi
```bash
python main.py
```

---

## ⚙️ Format Penulisan Prompt

Tempel prompt pada kotak teks di tab **Generate Video**, pisahkan antar prompt dengan **satu baris kosong**:

```text
Sebuah pemandangan drone kota futuristik saat matahari terbenam dengan mobil terbang

Close-up tangan robotik presisi tinggi menyentuh tangan manusia

Eksplorasi kehidupan bawah laut terumbu karang yang bercahaya di malam hari
```

---

## 📦 Build Standalone Executable (.exe)

Untuk membuat file `.exe` mandiri menggunakan PyInstaller:

```bash
pip install pyinstaller
pyinstaller AutoPix.spec
```

File hasil eksekutabel akan dibuat di folder `dist/AutoPix.exe`.

---

## 📝 Lisensi & Disclaimer

Proyek ini dilisensikan di bawah lisensi MIT.

> **Disclaimer:** Alat ini dibuat untuk tujuan pembelajaran, pengujian otomasi, dan penggunaan pribadi. Segala penyalahgunaan atau pelanggaran terhadap ketentuan layanan platform pihak ketiga sepenuhnya menjadi tanggung jawab masing-masing pengguna.

<br>
<p align="center"><b>© 2026 Jarot - All Rights Reserved.</b></p>

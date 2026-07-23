# 🚀 AutoPix

<p align="center">
  <img src="https://img.shields.io/badge/versi-3.0-7C3AED?style=flat-square" alt="Versi 3.0"/>
  <img src="https://img.shields.io/badge/python-3.10%2B-2563EB?style=flat-square" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/GUI-CustomTkinter-10B981?style=flat-square" alt="CustomTkinter"/>
  <img src="https://img.shields.io/badge/license-MIT-F59E0B?style=flat-square" alt="License MIT"/>
</p>

<p align="center">
  <b>Alat otomatisasi desktop untuk PixVerse</b>  <br/>
  Buat akun massal, generate video AI, dan kelola unduhan  semua dari GUI dark premium.
</p>

---

## ✨ Fitur

| Fitur | Deskripsi |
|-------|-----------|
| 🤖 **Buat Akun Massal** | Daftarkan ratusan akun PixVerse otomatis pakai temp-mail.ai + deteksi OTP |
| 🎥 **Generator Video AI** | Generate video batch dari teks prompt di banyak akun sekaligus |
| ⬇️ **Unduhan Cerdas** | Deteksi & download semua video yang sudah digenerate ke folder lokal |
| 🧵 **Eksekusi Paralel** | Semua browser berjalan bersamaan via `ThreadPoolExecutor` |
| 🛡️ **Browser Anti-Deteksi** | Pakai SeleniumBase + undetected-chromedriver agar tidak terdeteksi bot |
| ⚡ **React-Ready** | Penanganan input React/Vue native  kompatibel dengan SPA modern |
| 🌙 **Dark UI** | Tampilan dark premium dibangun dengan CustomTkinter |

---

## 🚀 Mulai Cepat

```bash
# 1. Clone repositori
git clone https://github.com/yourusername/autopix.git
cd autopix

# 2. Install dependensi
pip install customtkinter seleniumbase requests pillow

# 3. Jalankan
python main.py
```

### 🔧 Build ke Executable

```bash
pip install pyinstaller
pyinstaller main.spec
```

Hasil kompilasi ada di `dist/Auto Pixverse.exe`.

---

## 🧠 Cara Kerja

### 1. Pembuatan Akun
Membuka N browser secara bersamaan, mendaftar via temp-mail.ai, mengisi kode OTP otomatis, dan menyimpan sesi yang sudah login  siap pakai.

### 2. Generate Video
Mendistribusikan prompt secara round-robin ke semua akun yang aktif. Setiap akun memproses video yang ditugaskan secara konkuren. Popup "Maximum concurrent generations" ditangani otomatis.

### 3. Unduh
Transfer cookie dari sesi browser untuk mendownload video langsung  tanpa perlu login manual.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Buat       │────▶│  Generate    │────▶│  Unduh      │
│  Akun       │     │  Video       │     │  Video      │
└─────────────┘     └──────────────┘     └─────────────┘
```

---

## 🖥️ Tampilan Aplikasi

| Tab | Fungsi |
|-----|--------|
| **Buat Akun** | Atur jumlah akun, mulai/hentikan pendaftaran massal |
| **Generate Video** | Tempel prompt (pisahkan dengan baris kosong), generate batch |
| **Download** | Pilih folder, download semua video sekaligus |

---

## ⚙️ Konfigurasi

Tidak perlu environment variables. Semua autentikasi ditangani otomatis:

- **Email**: Inbox sementara via API [temp-mail.ai](https://temp-mail.ai)
- **Browser**: SeleniumBase dengan `uc=True` (mode undetected)
- **OTP**: Dipolling dari inbox dengan timeout 90 detik

### Format Prompt

Tempel beberapa prompt video di text box, pisahkan dengan **satu baris kosong**:

```
Sebuah drone shot sinematik kota futuristik saat matahari terbenam

Close-up tangan robot menyentuh tangan manusia

Eksplorasi bawah laut terumbu karang dengan makhluk bioluminescent
```

---

## 📁 Struktur Proyek

```
├── main.py                          # Entry point GUI
├── main.spec                        # Konfigurasi build PyInstaller
├── core/
│   ├── pixverse_creator.py          # Logika registrasi akun
│   ├── pixverse_video_generator.py  # Otomatisasi generate video
│   └── video_downloader.py          # Engine unduh video
├── dist/
│   └── Auto Pixverse.exe           # Executable siap pakai
├── .gitignore
└── README.md
```

---

## 🧪 Teknologi

| Teknologi | Kegunaan |
|-----------|----------|
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | Framework GUI dark modern |
| [SeleniumBase](https://seleniumbase.io/) | Otomatisasi browser anti-deteksi |
| [temp-mail.ai](https://temp-mail.ai) | API email sementara |
| [PyInstaller](https://pyinstaller.org/) | Python → Executable Windows |
| Python 3.10+ | Bahasa utama |

---

<p align="center">
  Dibuat dengan ⚡ oleh <b>Jarot</b>
</p>

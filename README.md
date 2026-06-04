# SIGADANA - Sistem Informasi Gelombang dan Angin Danau Toba

**SIGADANA** (Sistem Informasi Gelombang dan Angin Danau) adalah sebuah sistem prediksi yang menyajikan informasi real-time mengenai potensi bahaya pelayaran di Danau Toba. Sistem ini memberikan peringatan dini terhadap **gelombang tinggi, angin kencang, dan arus kuat**, yang berpotensi membahayakan aktivitas transportasi dan wisata di kawasan danau.

## 🌊 Apa Itu SIGADANA?

SIGADANA merupakan sistem berbasis web yang dirancang untuk:

- Memprediksi bahaya pelayaran akibat gelombang dan angin.
- Menyediakan informasi secara **real-time** untuk wilayah Danau Toba.
- Mengklasifikasikan tingkat bahaya berdasarkan **Gross Tonnage** dari kapal.
- Menggunakan pendekatan fisika berbasis data observasi cuaca dari wilayah pelabuhan.

## 🎯 Tujuan Pengembangan

Sistem ini bertujuan untuk membantu:

- **Masyarakat** umum di sekitar Danau Toba.
- **Nelayan dan operator transportasi** danau.
- **Wisatawan** yang beraktivitas di perairan.
- **Pihak berwenang** dalam pengambilan keputusan.

SIGADANA masih dalam tahap **prototipe** dan sedang diuji coba di wilayah Danau Toba. Ke depan, sistem ini diharapkan dapat dikembangkan dan diterapkan di wilayah perairan lain di Indonesia.

## 🚀 Fitur Utama

- ✅ Peringatan dini terhadap **gelombang tinggi**, **angin kencang**, dan **arus kuat**.
- ✅ Pemantauan terhadap **7 pelabuhan utama** di Danau Toba.
- ✅ Akses informasi yang **interaktif dan real-time** melalui website.

## 💻 Teknologi yang Digunakan

- Python (Flask)
- HTML5, CSS3
- Pandas, Numpy, Matplotlib
- Windrose, Geopy, Scipy
- Deployment berbasis server-side rendering

## ⚙️ Cara Menjalankan Proyek

### 1. Clone repository
```bash
git clone https://github.com/username/sigadana.git
cd sigadana
```

### 2. Buat virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Konfigurasi environment
```bash
cp .env.example .env
```
Lalu edit `.env` dan isi dengan nilai yang sesuai:
- `EMAIL_USER` & `EMAIL_PASS` — akun Gmail + App Password (bukan password biasa)
- `SECRET_KEY` — string acak untuk keamanan session Flask

### 5. Jalankan aplikasi
```bash
python run.py
```
Buka browser di `http://localhost:5000`

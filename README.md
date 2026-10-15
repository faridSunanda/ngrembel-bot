# 🌿 Bot Telegram & Web Admin Reservasi Wisata Ngrembel Asri Semarang

Sistem pemesanan tiket wisata dan manajemen reservasi online terpadu untuk **Wisata Ngrembel Asri Gunungpati Semarang**, menggabungkan **Bot Telegram interaktif** bagi pengunjung, **Payment Gateway QRIS Otomatis (Casaku API)**, dan **Web Admin Dashboard modern** bagi pengelola loket/manajemen wisata.

---

## 🌟 Fitur Utama

### 🤖 1. Bot Telegram Pengunjung
- **Pesan Welcome Ramah & Informatif (`/start`):** Memperkenalkan wahana unggulan Ngrembel Asri (kolam renang anak & ember tumpah, mini zoo / bird aviary, outbound, wahana ATV, paintball, pemancingan, dan resto lesehan).
- **Cek Harga Tiket & Paket:** Menampilkan daftar tiket reguler & paket wisata yang terdaftar dan aktif di database lengkap dengan harga dalam Rupiah.
- **Cek Jadwal Operasional:** Informasi jam buka hari biasa (weekday) dan akhir pekan (weekend/hari libur nasional).
- **Info Lokasi & Rute:** Alamat lengkap di Gunungpati Semarang, petunjuk fasilitas (parkir luas, mushola, gazebo, aula), dan tombol langsung menuju Google Maps.
- **Alur Reservasi Interaktif Terpadu:**
  1. 🗓 **Kalender Interaktif:** Memilih tanggal kunjungan langsung dari inline keyboard (navigasi bulan & pencegahan memilih tanggal lampau).
  2. 🎟 **Pilih Paket Wisata:** Memilih paket tiket yang terdaftar di database.
  3. 👥 **Pilih Jumlah Orang:** Tombol cepat (1, 2, 3, 4, 5, 10 orang) atau input manual langsung di chat.
  4. 👤 **Identitas & No. WhatsApp:** Konfirmasi nama pemesan dan nomor HP yang aktif.
  5. 💰 **Rincian Total Harga:** Menghitung total harga secara transparan dan meminta konfirmasi sebelum pembayaran.
  6. ⚡️ **Pembayaran QRIS Dinamis Otomatis (Casaku):** Bot otomatis membuat QRIS dinamis ber-kode unik acak via Casaku API v2 dan mengirimkan gambar QR Code langsung ke chat Telegram!
  7. 🔄 **Verifikasi Otomatis Real-Time:** Sistem otomatis memantau status pembayaran setiap beberapa detik dan menerima webhook dari Casaku tanpa perlu upload bukti transfer.
  8. 🔖 **Kode Booking Unik & E-Tiket Ringkas:** Menghasilkan kode unik seperti `NGR-20261015-XXXX` yang dapat ditunjukkan di loket masuk.
- **Cek Status Reservasi Mandiri:** Pengunjung bisa memeriksa riwayat dan status tiket mereka kapan saja.

---

### 💳 2. Integrasi Payment Gateway Casaku (https://casaku.id)
- **Generate QRIS v2 (`POST /api/generate/v2/qris`):** Mengubah QRIS statis merchant menjadi QRIS dinamis otomatis dengan penyisipan kode unik acak 1–999.
- **Dukungan Multi-E-Wallet & Bank:** Dapat di-scan menggunakan DANA, GoPay, OVO, ShopeePay, LinkAja, BCA, Mandiri, BRI, BNI, dan semua aplikasi mobile banking.
- **Webhook Callback (`POST /api/webhook/casaku`):** Notifikasi instan saat pembayaran berhasil dengan verifikasi tanda tangan HMAC-SHA256 (`X-Casaku-Signature`).
- **Background Watcher:** Bot secara proaktif mengecek status transaksi ke Casaku dan otomatis memberikan tiket aktif saat dana masuk.

---

### 💻 3. Web Admin Dashboard (Pengelola Wisata)
- **Dashboard Overview:** Metrik real-time mencakup total reservasi, reservasi pending, reservasi aktif/dikonfirmasi, dan total pendapatan tiket (Rp).
- **Kelola Data Wisata & Tiket (CRUD Lengkap):**
  - Tambah paket wisata baru (nama, kategori, harga, deskripsi fasilitas).
  - Edit paket wisata yang sudah ada.
  - Hapus paket wisata.
  - Toggle status tayang (Aktif / Nonaktif) agar fleksibel mengatur promo atau perubahan harga tiket.
- **Kelola Daftar Reservasi:**
  - Filter status (Semua, Pending, Cek Bukti, Dikonfirmasi, Selesai, Ditolak).
  - Kotak pencarian cerdas (berdasarkan kode booking, nama pemesan, nomor HP, atau ID transaksi Casaku).
  - Modal detail reservasi lengkap dengan informasi transaksi Casaku / bukti transfer.
  - Tombol cepat **Chat WhatsApp** langsung ke nomor pelanggan.
  - **Notifikasi Otomatis ke Telegram Pelanggan:** Saat admin mengubah status reservasi, sistem otomatis mengirimkan pesan konfirmasi ke bot Telegram pengguna secara *real-time*!
- **Pengaturan Wisata & Konfigurasi Casaku:**
  - Input License Key, QR ID, Webhook Secret, dan Package ID Casaku.
  - Tombol uji coba koneksi perangkat listener Android Casaku.
  - Edit jam buka, alamat lokasi, link Google Maps, kontak CS.

---

## 📁 Struktur Direktori

```
ngrembelBot/
├── app.md                  # Spesifikasi & alur dari pengguna
├── .env                    # File konfigurasi lokal (Token bot, Casaku keys, kredensial admin)
├── .env.example            # Contoh template variabel lingkungan
├── config.py               # Konfigurasi aplikasi & direktori
├── casaku.py               # Layanan integrasi Casaku API (QRIS v2, status, webhook, render QR)
├── database.py             # Schema SQLite, seeding awal, & query helper
├── telegram_calendar.py    # Modul kalender inline keyboard interaktif
├── bot.py                  # Logika bot Telegram & alur reservasi
├── web_app.py              # Server web FastAPI & backend dashboard admin
├── run.py                  # Script runner utama (menjalankan Bot & Web bersamaan)
├── static/
│   ├── css/
│   │   └── style.css       # Desain modern bernuansa Emerald & Slate
│   ├── js/
│   │   └── admin.js        # Logika interaktif admin, modal, & filter
│   └── uploads/            # Direktori penyimpanan bukti transfer pembayaran
├── templates/
│   ├── base.html           # Layout utama dashboard & navigasi
│   ├── login.html          # Halaman login admin glassmorphism
│   ├── dashboard.html      # Tinjauan statistik & tabel reservasi terbaru
│   ├── wisata.html         # Manajemen CRUD paket wisata & tiket
│   ├── reservations.html   # Manajemen reservasi, pencarian, & filter
│   └── settings.html       # Form pengaturan informasi wisata & Casaku
└── README.md               # Dokumentasi lengkap
```

---

## 🚀 Panduan Menjalankan & Mengonfigurasi Casaku

### 1. Masukkan Kredensial di File [`.env`](file:///d:/farid/faridproject/ngrembelBot/.env)

```env
# Bot Telegram
BOT_TOKEN=7739470286:AAGwqqGKOua26qymJbZxq4bzjtQY8wKsHWw

# Payment Gateway Casaku (https://casaku.id)
CASAKU_LICENSE_KEY=YOUR_CASAKU_LICENSE_KEY
CASAKU_QR_ID=YOUR_CASAKU_QR_ID_UUID
CASAKU_WEBHOOK_SECRET=YOUR_CASAKU_WEBHOOK_SECRET
CASAKU_PACKAGE_ID=id.dana

# Kredensial Admin Web
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
WEB_HOST=0.0.0.0
WEB_PORT=8000
```

> **Cara Mendapatkan Kredensial Casaku:**
> 1. Buat akun di [casaku.id](https://casaku.id).
> 2. Unggah gambar QRIS statis Anda di [casaku.id/qris](https://casaku.id/qris) untuk mendapatkan **QR ID (UUID)**.
> 3. Generate **License Key** & **Webhook Secret** di [casaku.id/api-keys](https://casaku.id/api-keys).
> 4. Instal aplikasi *Casaku : Gateway Qris* di HP Android Anda, login, nyalakan *Listener App*, dan pastikan checklist berwarna hijau.

---

### 2. Tarif Tiket Uji Coba (Under Rp 1.000)
Untuk keperluan pengujian transaksi nyata dengan nominal kecil, harga seluruh paket tiket telah diset di bawah Rp 1.000:
- **Tiket Masuk Reguler (Weekday):** Rp 100
- **Tiket Masuk Reguler (Weekend):** Rp 200
- **Paket Terusan Anak Lengkap:** Rp 250
- **Paket Flying Fox & ATV:** Rp 300
- **Paket Outbound Seru & Paintball:** Rp 500
- **Paket Pemancingan & Lesehan:** Rp 700

*(Tarif ini dapat diubah kapan saja melalui menu **Kelola Wisata & Tiket** di Web Admin).*

---

### 3. Jalankan Aplikasi
Jalankan file [`run.py`](file:///d:/farid/faridproject/ngrembelBot/run.py):

```bash
python run.py
```

Buka Telegram dan ketik `/start` pada `@rydds_bot`, lalu coba alur reservasi tiket untuk melihat QRIS dinamis otomatis!
Akses Dashboard Admin di: **[http://localhost:8000](http://localhost:8000)** (Username: `admin`, Password: `admin123`).

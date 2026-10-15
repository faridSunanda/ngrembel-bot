import sqlite3
import hashlib
from datetime import datetime
from config import (
    DB_PATH,
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
    CASAKU_LICENSE_KEY,
    CASAKU_QR_ID,
    CASAKU_WEBHOOK_SECRET,
    CASAKU_PACKAGE_ID,
)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Tabel Wisata / Paket Tiket
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wisata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'Tiket',
        price INTEGER NOT NULL,
        description TEXT,
        image_url TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Tabel Reservasi
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_code TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        user_name TEXT NOT NULL,
        user_phone TEXT NOT NULL,
        ticket_id INTEGER NOT NULL,
        visit_date TEXT NOT NULL,
        ticket_qty INTEGER NOT NULL DEFAULT 1,
        total_price INTEGER NOT NULL,
        payment_method TEXT DEFAULT 'QRIS Otomatis (Casaku)',
        payment_proof TEXT,
        status TEXT DEFAULT 'PENDING',
        admin_notes TEXT,
        casaku_trx_id TEXT,
        qr_string TEXT,
        payment_amount INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ticket_id) REFERENCES wisata(id) ON DELETE CASCADE
    )
    """)

    # Migrasi kolom tambahan di tabel reservations jika belum ada
    columns_to_add = [
        ("casaku_trx_id", "TEXT"),
        ("qr_string", "TEXT"),
        ("payment_amount", "INTEGER")
    ]
    cursor.execute("PRAGMA table_info(reservations)")
    existing_cols = [row["name"] for row in cursor.fetchall()]
    for col_name, col_type in columns_to_add:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE reservations ADD COLUMN {col_name} {col_type}")

    # 3. Tabel Pengaturan / Settings Info
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    # 4. Tabel Admin Users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Seed Admin User default jika belum ada
    cursor.execute("SELECT id FROM admin_users WHERE username = ?", (ADMIN_USERNAME,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO admin_users (username, password_hash, full_name) VALUES (?, ?, ?)",
            (ADMIN_USERNAME, hash_password(ADMIN_PASSWORD), "Administrator Ngrembel Asri")
        )

    # Seed Settings default
    default_settings = {
        "opening_hours": "🗓 Setiap Hari (Senin - Minggu): 08.30 - 16.30 WIB\n🍽 Restoran & Pemancingan: s/d 21.00 WIB",
        "location_address": "📍 Jl. Raya Manyaran-Gunungpati No. KM 10, Kel. Sadeng, Kec. Gunungpati, Kota Semarang, Jawa Tengah 50222",
        "maps_url": "https://maps.app.goo.gl/9dG1Vq8JbV3U7g5d6",
        "phone_contact": "📞 WhatsApp / CS: 0812-3456-7890\n☎️ Telepon: (024) 6932145",
        "bank_info": "💳 Bank BCA: 1234567890 a.n. Ngrembel Asri Wisata\n💳 Bank BRI: 098701020304506 a.n. Ngrembel Asri Wisata\n💳 Bank Mandiri: 1350098765432 a.n. Ngrembel Asri Wisata",
        "qris_info": "📲 QRIS Otomatis Casaku aktif. Scan langsung dari GoPay, DANA, OVO, ShopeePay, BCA, atau m-banking.",
        "casaku_license_key": CASAKU_LICENSE_KEY,
        "casaku_qr_id": CASAKU_QR_ID,
        "casaku_webhook_secret": CASAKU_WEBHOOK_SECRET,
        "casaku_package_id": CASAKU_PACKAGE_ID or "id.dana"
    }
    for k, v in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Seed / Update Paket Wisata dengan harga di bawah Rp 1.000 untuk pengujian pembayaran real!
    test_wisata = [
        ("Tiket Masuk Reguler (Weekday)", "Tiket Masuk", 100, "Tiket masuk per orang hari Senin-Jumat. Akses kolam renang anak & ember tumpah, taman satwa / bird aviary, dan omah playon gratis.", 1),
        ("Tiket Masuk Reguler (Weekend / Libur)", "Tiket Masuk", 200, "Tiket masuk per orang hari Sabtu, Minggu & Hari Libur Nasional. Akses kolam renang anak, mini zoo, kura-kura raksasa, & area santai gratis.", 1),
        ("Paket Petualangan Flying Fox & ATV", "Paket Wahana", 300, "Termasuk tiket masuk + 1x Wahana Flying Fox Dino/Jungle + 1x Naik ATV trek petualangan + terapi ikan.", 1),
        ("Paket Outbound Seru & Paintball (Min. 5 org)", "Paket Gathering", 500, "Per orang (Min 5 org). Termasuk tiket masuk, perlengkapan paintball lengkap, 50 peluru, instruktur & area arena khusus.", 1),
        ("Paket Pemancingan & Lesehan Keluarga", "Paket Kuliner", 700, "Termasuk sewa 2 alat pancing + umpan, voucher kuliner lesehan, dan akses seluruh wahana gratis.", 1),
        ("Paket Terusan Anak Lengkap", "Paket Anak", 250, "Tiket masuk + naik Kereta Mini + Mini Boat + Kuda Tunggang + Bungee Trampoline.", 1)
    ]

    cursor.execute("SELECT COUNT(*) as count FROM wisata")
    count = cursor.fetchone()["count"]
    if count == 0:
        cursor.executemany(
            "INSERT INTO wisata (name, category, price, description, is_active) VALUES (?, ?, ?, ?, ?)",
            test_wisata
        )
    else:
        # Update existing wisata prices to be under Rp 1.000 for test real payment
        for name, category, price, desc, is_act in test_wisata:
            cursor.execute(
                "UPDATE wisata SET price = ? WHERE name = ? AND price > 1000",
                (price, name)
            )

    conn.commit()
    conn.close()

# --- Query Helpers ---

def get_wisata_list(active_only=False):
    conn = get_db()
    if active_only:
        rows = conn.execute("SELECT * FROM wisata WHERE is_active = 1 ORDER BY price ASC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM wisata ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_wisata_by_id(wisata_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM wisata WHERE id = ?", (wisata_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_wisata(name: str, category: str, price: int, description: str, is_active: int = 1):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO wisata (name, category, price, description, is_active) VALUES (?, ?, ?, ?, ?)",
        (name, category, price, description, is_active)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id

def update_wisata(wisata_id: int, name: str, category: str, price: int, description: str, is_active: int):
    conn = get_db()
    conn.execute(
        "UPDATE wisata SET name = ?, category = ?, price = ?, description = ?, is_active = ? WHERE id = ?",
        (name, category, price, description, is_active, wisata_id)
    )
    conn.commit()
    conn.close()

def delete_wisata(wisata_id: int):
    conn = get_db()
    conn.execute("DELETE FROM wisata WHERE id = ?", (wisata_id,))
    conn.commit()
    conn.close()

def create_reservation(booking_code: str, user_id: int, user_name: str, user_phone: str,
                       ticket_id: int, visit_date: str, ticket_qty: int, total_price: int,
                       payment_method: str = "QRIS Otomatis (Casaku)", payment_proof: str = None,
                       casaku_trx_id: str = None, qr_string: str = None, payment_amount: int = None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reservations (
            booking_code, user_id, user_name, user_phone, ticket_id,
            visit_date, ticket_qty, total_price, payment_method, payment_proof,
            status, casaku_trx_id, qr_string, payment_amount
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?)
    """, (
        booking_code, user_id, user_name, user_phone, ticket_id,
        visit_date, ticket_qty, total_price, payment_method, payment_proof,
        casaku_trx_id, qr_string, payment_amount or total_price
    ))
    conn.commit()
    res_id = cur.lastrowid
    conn.close()
    return res_id

def update_reservation_casaku(res_id: int, casaku_trx_id: str, qr_string: str, payment_amount: int):
    conn = get_db()
    conn.execute("""
        UPDATE reservations
        SET casaku_trx_id = ?, qr_string = ?, payment_amount = ?
        WHERE id = ?
    """, (casaku_trx_id, qr_string, payment_amount, res_id))
    conn.commit()
    conn.close()

def mark_reservation_paid_by_casaku(casaku_trx_id: str, paid_amount: int = None):
    conn = get_db()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()
    cur.execute("""
        UPDATE reservations
        SET status = 'PAID',
            admin_notes = COALESCE(admin_notes, '') || ' [Pembayaran QRIS Casaku terverifikasi otomatis]',
            updated_at = ?
        WHERE casaku_trx_id = ? AND status IN ('PENDING', 'PAID')
    """, (now_str, casaku_trx_id))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0

def get_reservation_by_casaku_trx(casaku_trx_id: str):
    conn = get_db()
    row = conn.execute("""
        SELECT r.*, w.name as ticket_name, w.category as ticket_category, w.price as ticket_unit_price
        FROM reservations r
        LEFT JOIN wisata w ON r.ticket_id = w.id
        WHERE r.casaku_trx_id = ?
    """, (casaku_trx_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_reservations(status: str = None, search: str = None):
    conn = get_db()
    query = """
        SELECT r.*, w.name as ticket_name, w.category as ticket_category, w.price as ticket_unit_price
        FROM reservations r
        LEFT JOIN wisata w ON r.ticket_id = w.id
        WHERE 1=1
    """
    params = []
    if status and status != "ALL":
        query += " AND r.status = ?"
        params.append(status)
    if search:
        query += " AND (r.booking_code LIKE ? OR r.user_name LIKE ? OR r.user_phone LIKE ? OR r.casaku_trx_id LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    query += " ORDER BY r.id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_reservation_by_code(booking_code: str):
    conn = get_db()
    row = conn.execute("""
        SELECT r.*, w.name as ticket_name, w.category as ticket_category, w.price as ticket_unit_price
        FROM reservations r
        LEFT JOIN wisata w ON r.ticket_id = w.id
        WHERE r.booking_code = ?
    """, (booking_code,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_reservation_by_id(res_id: int):
    conn = get_db()
    row = conn.execute("""
        SELECT r.*, w.name as ticket_name, w.category as ticket_category, w.price as ticket_unit_price
        FROM reservations r
        LEFT JOIN wisata w ON r.ticket_id = w.id
        WHERE r.id = ?
    """, (res_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_reservation_status(res_id: int, status: str, admin_notes: str = None):
    conn = get_db()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if admin_notes is not None:
        conn.execute(
            "UPDATE reservations SET status = ?, admin_notes = ?, updated_at = ? WHERE id = ?",
            (status, admin_notes, now_str, res_id)
        )
    else:
        conn.execute(
            "UPDATE reservations SET status = ?, updated_at = ? WHERE id = ?",
            (status, now_str, res_id)
        )
    conn.commit()
    conn.close()

def delete_reservation(res_id: int):
    conn = get_db()
    conn.execute("DELETE FROM reservations WHERE id = ?", (res_id,))
    conn.commit()
    conn.close()

def get_dashboard_stats():
    conn = get_db()
    total_res = conn.execute("SELECT COUNT(*) as c FROM reservations").fetchone()["c"]
    pending_res = conn.execute("SELECT COUNT(*) as c FROM reservations WHERE status = 'PENDING'").fetchone()["c"]
    confirmed_res = conn.execute("SELECT COUNT(*) as c FROM reservations WHERE status IN ('CONFIRMED', 'PAID')").fetchone()["c"]
    completed_res = conn.execute("SELECT COUNT(*) as c FROM reservations WHERE status = 'COMPLETED'").fetchone()["c"]
    
    revenue_row = conn.execute("SELECT SUM(total_price) as s FROM reservations WHERE status IN ('CONFIRMED', 'PAID', 'COMPLETED')").fetchone()
    total_revenue = revenue_row["s"] if revenue_row["s"] is not None else 0

    total_tickets = conn.execute("SELECT COUNT(*) as c FROM wisata WHERE is_active = 1").fetchone()["c"]
    
    conn.close()
    return {
        "total_reservations": total_res,
        "pending_reservations": pending_res,
        "confirmed_reservations": confirmed_res,
        "completed_reservations": completed_res,
        "total_revenue": total_revenue,
        "total_active_tickets": total_tickets
    }

def get_settings():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

def update_setting(key: str, value: str):
    conn = get_db()
    conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
    conn.commit()
    conn.close()

def verify_admin(username: str, password: str):
    conn = get_db()
    pw_hash = hash_password(password)
    user = conn.execute("SELECT * FROM admin_users WHERE username = ? AND password_hash = ?", (username, pw_hash)).fetchone()
    conn.close()
    return dict(user) if user else None

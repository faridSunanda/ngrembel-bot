import io
from datetime import datetime
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import qrcode

def format_rupiah(amount: int) -> str:
    return f"Rp {amount:,.0f}".replace(",", ".")

def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """
    Memuat font TrueType bawaan Windows dengan fallback aman jika file tidak ditemukan.
    """
    font_names = (
        ["arialbd.ttf", "segoeuib.ttf", "tahomabd.ttf"]
        if bold
        else ["arial.ttf", "segoeui.ttf", "tahoma.ttf"]
    )
    for font_name in font_names:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None

def generate_ticket_invoice(
    booking_code: str,
    user_name: str,
    user_phone: str,
    ticket_name: str,
    visit_date: str,
    ticket_qty: int,
    total_price: int,
    payment_method: str = "QRIS Otomatis (Casaku)",
    created_at: Optional[str] = None,
    status: str = "LUNAS / VERIFIED"
) -> io.BytesIO:
    """
    Membuat gambar E-Tiket / Invoice Resmi Wisata Ngrembel Asri
    dalam format PNG beresolusi tinggi (800 x 1200 px).
    """
    w, h = 800, 1220
    im = Image.new("RGB", (w, h), "#f1f5f9") # Background luar abu-abu elegan
    draw = ImageDraw.Draw(im)

    # Inisialisasi Font
    f_brand = get_font(28, bold=True)
    f_brand_sub = get_font(15, bold=False)
    f_badge = get_font(13, bold=True)
    f_bcode = get_font(32, bold=True)
    f_label = get_font(12, bold=False)
    f_value = get_font(16, bold=True)
    f_total_label = get_font(13, bold=False)
    f_total_val = get_font(26, bold=True)
    f_subtext = get_font(12, bold=False)
    f_note_title = get_font(13, bold=True)
    f_note_body = get_font(11, bold=False)

    # 1. Main Card Background (Putih dengan sudut melengkung)
    card_x1, card_y1, card_x2, card_y2 = 35, 35, 765, 1185
    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=24, fill="#ffffff")

    # 2. Header Banner Hijau Emerald Ngrembel
    header_h = 165
    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y1 + header_h], radius=24, fill="#064e3b")
    # Ratakan sudut bawah header agar menempel ke badan tiket
    draw.rectangle([card_x1, card_y1 + header_h - 24, card_x2, card_y1 + header_h], fill="#064e3b")

    # Teks Brand
    draw.text((65, 60), "WISATA NGREMBEL ASRI", fill="#ffffff", font=f_brand)
    draw.text((65, 102), "Gunungpati, Semarang • E-Tiket Masuk & Invoice Resmi", fill="#a7f3d0", font=f_brand_sub)
    draw.text((65, 126), "Jl. Raya Manyaran-Gunungpati Km 10 • Telp: 0812-3456-7890", fill="#6ee7b7", font=f_subtext)

    # Badge Status (Sudut Kanan Atas)
    badge_w, badge_h = 175, 36
    bx1 = card_x2 - badge_w - 25
    by1 = 65
    draw.rounded_rectangle([bx1, by1, bx1 + badge_w, by1 + badge_h], radius=18, fill="#059669")
    draw.text((bx1 + 18, by1 + 9), "VERIFIED / LUNAS", fill="#ffffff", font=f_badge)

    # 3. Bagian QR Code & Kode Booking
    # Buat QR Code berisi kode booking dan informasi verifikasi
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(f"NGREMBEL:{booking_code}|{user_name}|{ticket_name}|{visit_date}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#064e3b", back_color="#ffffff")
    pil_qr = qr_img.get_image()
    qr_w, qr_h = pil_qr.size

    # Frame QR Code
    qr_top = card_y1 + header_h + 20
    qr_box_pad = 8
    qbx1 = (w - qr_w) // 2 - qr_box_pad
    qby1 = qr_top - qr_box_pad
    qbx2 = qbx1 + qr_w + (qr_box_pad * 2)
    qby2 = qby1 + qr_h + (qr_box_pad * 2)
    draw.rounded_rectangle([qbx1, qby1, qbx2, qby2], radius=12, fill="#f8fafc", outline="#e2e8f0", width=2)
    im.paste(pil_qr, ((w - qr_w) // 2, qr_top))

    # Kode Booking Teks Besar
    bcode_y = qby2 + 16
    draw.text(((w - 180) // 2, bcode_y), "KODE BOOKING TIKET", fill="#64748b", font=f_label)
    
    b_box = draw.textbbox((0, 0), booking_code, font=f_bcode)
    bw = b_box[2] - b_box[0]
    draw.text(((w - bw) // 2, bcode_y + 20), booking_code, fill="#064e3b", font=f_bcode)

    hint_text = "Tunjukkan QR Code ini kepada petugas loket di pintu masuk"
    h_box = draw.textbbox((0, 0), hint_text, font=f_subtext)
    hw = h_box[2] - h_box[0]
    draw.text(((w - hw) // 2, bcode_y + 64), hint_text, fill="#64748b", font=f_subtext)

    # 4. Garis Perforasi Tiket (Perforated Divider)
    cutout_y = bcode_y + 95
    radius_notch = 18
    # Notches (Lingkaran pemotong tiket di kiri dan kanan)
    draw.pieslice([card_x1 - radius_notch, cutout_y - radius_notch, card_x1 + radius_notch, cutout_y + radius_notch], 270, 90, fill="#f1f5f9")
    draw.pieslice([card_x2 - radius_notch, cutout_y - radius_notch, card_x2 + radius_notch, cutout_y + radius_notch], 90, 270, fill="#f1f5f9")
    
    # Garis titik-titik (dashed) di antara kedua notch
    dash_start_x = card_x1 + radius_notch + 10
    dash_end_x = card_x2 - radius_notch - 10
    cx = dash_start_x
    while cx < dash_end_x:
        draw.line([(cx, cutout_y), (min(cx + 8, dash_end_x), cutout_y)], fill="#cbd5e1", width=2)
        cx += 14

    # 5. Detail Reservasi (Grid 2 Kolom Rapi)
    details_y = cutout_y + 25
    col1_x = card_x1 + 35
    col2_x = card_x1 + 380

    def draw_detail_item(x, y, label, value):
        draw.text((x, y), label.upper(), fill="#64748b", font=f_label)
        draw.text((x, y + 18), str(value), fill="#0f172a", font=f_value)

    # Baris 1: Paket Wisata & Jumlah Orang
    draw_detail_item(col1_x, details_y, "Paket Wisata", ticket_name)
    draw_detail_item(col2_x, details_y, "Jumlah Pengunjung", f"{ticket_qty} Orang")

    # Baris 2: Tanggal Kunjungan & Waktu Kunjungan
    draw_detail_item(col1_x, details_y + 58, "Tanggal Kunjungan", visit_date)
    draw_detail_item(col2_x, details_y + 58, "Jam Buka Operasional", "08:30 - 17:00 WIB")

    # Baris 3: Nama Pemesan & No WhatsApp
    draw_detail_item(col1_x, details_y + 116, "Nama Pemesan", user_name)
    draw_detail_item(col2_x, details_y + 116, "No. WhatsApp", user_phone)

    # 6. Box Total Pembayaran (Emerald Soft Card)
    box_total_y = details_y + 175
    box_total_h = 75
    bx1 = card_x1 + 25
    bx2 = card_x2 - 25
    draw.rounded_rectangle([bx1, box_total_y, bx2, box_total_y + box_total_h], radius=14, fill="#ecfdf5", outline="#a7f3d0", width=2)
    
    draw.text((bx1 + 25, box_total_y + 16), "TOTAL PEMBAYARAN", fill="#047857", font=f_total_label)
    draw.text((bx1 + 25, box_total_y + 36), f"Metode: {payment_method}", fill="#059669", font=f_subtext)
    
    total_str = format_rupiah(total_price)
    t_box = draw.textbbox((0, 0), total_str, font=f_total_val)
    tw = t_box[2] - t_box[0]
    draw.text((bx2 - tw - 25, box_total_y + 22), total_str, fill="#064e3b", font=f_total_val)

    # 7. Ketentuan & Syarat Masuk (Footer Tiket)
    footer_y = box_total_y + box_total_h + 20
    draw.text((card_x1 + 30, footer_y), "SYARAT & KETENTUAN KUNJUNGAN:", fill="#475569", font=f_note_title)
    
    notes = [
        "1. Tiket ini merupakan bukti sah pembayaran dan tanda masuk ke kawasan Wisata Ngrembel Asri.",
        "2. Tunjukkan gambar e-tiket ini kepada petugas di loket pintu masuk untuk diverifikasi.",
        "3. Tiket hanya berlaku sesuai tanggal kunjungan tertera untuk 1 (satu) kali kunjungan.",
        "4. Dilarang membawa senjata tajam, narkotika, minuman beralkohol, dan hewan peliharaan.",
    ]
    
    cur_y = footer_y + 22
    for n in notes:
        draw.text((card_x1 + 30, cur_y), n, fill="#64748b", font=f_note_body)
        cur_y += 18

    # Watermark / Timestamp Pembuatan
    now_str = created_at or datetime.now().strftime("%d/%m/%Y %H:%M WIB")
    foot_stamp = f"E-Tiket Resmi diterbitkan pada: {now_str} • Wisata Ngrembel Asri Gunungpati Semarang"
    draw.text((card_x1 + 30, card_y2 - 28), foot_stamp, fill="#94a3b8", font=f_subtext)

    # Output ke memory BytesIO
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    buf.seek(0)
    return buf

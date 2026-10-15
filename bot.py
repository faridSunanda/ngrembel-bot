import asyncio
import io
import logging
import random
import string
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import database
import casaku
from ticket_generator import generate_ticket_invoice
from telegram_calendar import create_calendar, MONTH_NAMES_ID
from config import BOT_TOKEN, UPLOAD_DIR

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation States
(
    STATE_SELECT_DATE,
    STATE_SELECT_TICKET,
    STATE_SELECT_QTY,
    STATE_INPUT_NAME,
    STATE_INPUT_PHONE,
    STATE_CONFIRM_BOOKING,
    STATE_WAIT_PAYMENT_PROOF,
) = range(7)

def generate_booking_code() -> str:
    date_str = datetime.now().strftime("%Y%m%d")
    rand_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"NGR-{date_str}-{rand_suffix}"

def format_rupiah(amount: int) -> str:
    return f"Rp {amount:,.0f}".replace(",", ".")

def get_main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📅 Reservasi Tiket Wisata", callback_data="MENU_RESERVATION")
        ],
        [
            InlineKeyboardButton("🎟 Cek Harga Tiket", callback_data="MENU_PRICES"),
            InlineKeyboardButton("🕒 Jadwal Buka", callback_data="MENU_HOURS")
        ],
        [
            InlineKeyboardButton("📍 Lokasi & Rute", callback_data="MENU_LOCATION"),
            InlineKeyboardButton("🔍 Cek Reservasi", callback_data="MENU_CHECK_STATUS")
        ],
        [
            InlineKeyboardButton("📞 Hubungi Kami", callback_data="MENU_CONTACT")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    first_name = user.first_name if user else "Pengunjung"

    welcome_text = (
        f"🌿 *Selamat Datang di Bot Wisata Ngrembel Asri Semarang, {first_name}!* 🌿\n\n"
        "Nikmati rekreasi keluarga terlengkap bernuansa alam pedesaan di Gunungpati, Semarang:\n"
        "• 🏊 Kolam Renang Anak & Ember Tumpah\n"
        "• 🦜 Mini Zoo / Bird Aviary & Kura-kura Raksasa\n"
        "• 🎯 Outbound, ATV, Paintball, Flying Fox\n"
        "• 🎣 Pemancingan & Kuliner Lesehan Ikan Bakar\n\n"
        "Silakan pilih menu di bawah ini untuk memulai reservasi atau mencari informasi:"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )

async def show_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tickets = database.get_wisata_list(active_only=True)
    if not tickets:
        msg = "Saat ini belum ada data tiket wisata yang aktif."
    else:
        msg = "🎟 *DAFTAR HARGA TIKET & PAKET WISATA NGREMBEL ASRI* 🎟\n\n"
        for t in tickets:
            msg += f"✨ *{t['name']}* ({t['category']})\n"
            msg += f"   💰 Harga: *{format_rupiah(t['price'])}* / orang\n"
            if t['description']:
                msg += f"   ℹ️ _{t['description']}_\n"
            msg += "\n"
        msg += "💡 _Tarif promo uji coba sistem aktif._"

    keyboard = [
        [InlineKeyboardButton("📅 Pesan Tiket Sekarang", callback_data="MENU_RESERVATION")],
        [InlineKeyboardButton("🔙 Menu Utama", callback_data="MENU_BACK_MAIN")]
    ]
    await query.edit_message_text(
        text=msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def show_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    settings = database.get_settings()
    hours_info = settings.get("opening_hours", "08.30 - 16.30 WIB")

    msg = (
        "🕒 *JADWAL OPERASIONAL WISATA NGREMBEL ASRI* 🕒\n\n"
        f"{hours_info}\n\n"
        "💡 *Tips Berkunjung:*\n"
        "• Disarankan datang pagi hari (08.30 - 10.00) untuk menikmati udara sejuk & wahana tanpa antre.\n"
        "• Restoran dan area santai buka hingga malam hari untuk makan bersama keluarga."
    )

    keyboard = [
        [InlineKeyboardButton("📅 Reservasi Tiket", callback_data="MENU_RESERVATION")],
        [InlineKeyboardButton("🔙 Menu Utama", callback_data="MENU_BACK_MAIN")]
    ]
    await query.edit_message_text(
        text=msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def show_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    settings = database.get_settings()
    address = settings.get("location_address", "Jl. Raya Manyaran-Gunungpati KM 10, Semarang")
    maps_url = settings.get("maps_url", "https://maps.app.goo.gl/9dG1Vq8JbV3U7g5d6")

    msg = (
        "📍 *LOKASI & AKSES WISATA NGREMBEL ASRI* 📍\n\n"
        f"Alamat:\n{address}\n\n"
        "🚗 *Fasilitas Pengunjung:*\n"
        "• Area parkir luas (bus, mobil, motor)\n"
        "• Mushola bersih & tempat wudhu luas\n"
        "• Gazebo & saung lesehan istirahat\n"
        "• Toilet & ruang bilas kolam renang\n"
        "• Aula gathering / pertemuan keluarga & rombongan"
    )

    keyboard = [
        [InlineKeyboardButton("🗺 Buka Google Maps", url=maps_url)],
        [InlineKeyboardButton("📅 Reservasi Tiket", callback_data="MENU_RESERVATION")],
        [InlineKeyboardButton("🔙 Menu Utama", callback_data="MENU_BACK_MAIN")]
    ]
    await query.edit_message_text(
        text=msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def show_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    settings = database.get_settings()
    contact = settings.get("phone_contact", "0812-3456-7890")

    msg = (
        "📞 *KONTAK & BANTUAN WISATA NGREMBEL ASRI* 📞\n\n"
        "Ada pertanyaan mengenai tiket rombongan, sewa aula gathering, atau reservasi khusus?\n\n"
        f"{contact}\n\n"
        "Tim Customer Service kami siap melayani Anda setiap hari."
    )

    keyboard = [
        [InlineKeyboardButton("📅 Reservasi Tiket", callback_data="MENU_RESERVATION")],
        [InlineKeyboardButton("🔙 Menu Utama", callback_data="MENU_BACK_MAIN")]
    ]
    await query.edit_message_text(
        text=msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def check_reservation_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    reservations = database.get_reservations()
    user_res = [r for r in reservations if r["user_id"] == user_id]

    if not user_res:
        msg = (
            "🔍 *CEK STATUS RESERVASI*\n\n"
            "Anda belum memiliki riwayat reservasi di Wisata Ngrembel Asri.\n"
            "Silakan buat reservasi baru melalui tombol di bawah:"
        )
        keyboard = [
            [InlineKeyboardButton("📅 Buat Reservasi Sekarang", callback_data="MENU_RESERVATION")],
            [InlineKeyboardButton("🔙 Menu Utama", callback_data="MENU_BACK_MAIN")]
        ]
    else:
        msg = "📋 *DAFTAR RESERVASI ANDA* 📋\n\n"
        for r in user_res[:5]:
            status_emoji = {
                "PENDING": "⏳ Menunggu Pembayaran/Verifikasi",
                "CONFIRMED": "✅ Dikonfirmasi / Tiket Aktif",
                "PAID": "💵 Pembayaran Diterima",
                "COMPLETED": "🎉 Selesai Digunakan",
                "REJECTED": "❌ Dibatalkan / Ditolak"
            }.get(r["status"], r["status"])

            amount_show = r.get("payment_amount") or r["total_price"]

            msg += f"🔖 *Kode Booking:* `{r['booking_code']}`\n"
            msg += f"🎟 *Paket:* {r['ticket_name']}\n"
            msg += f"📅 *Tanggal Kunjungan:* {r['visit_date']}\n"
            msg += f"👥 *Jumlah:* {r['ticket_qty']} Orang\n"
            msg += f"💰 *Total:* {format_rupiah(amount_show)}\n"
            msg += f"📌 *Status:* {status_emoji}\n"
            if r.get("admin_notes"):
                msg += f"💬 *Catatan:* _{r['admin_notes']}_\n"
            msg += "---------------------------------\n"

        keyboard = []
        for r in user_res[:5]:
            if r["status"] in ("CONFIRMED", "COMPLETED"):
                keyboard.append([
                    InlineKeyboardButton(f"🎫 Lihat E-Tiket ({r['booking_code']})", callback_data=f"VIEW_TICKET:{r['id']}")
                ])
        keyboard.append([InlineKeyboardButton("📅 Buat Reservasi Baru", callback_data="MENU_RESERVATION")])
        keyboard.append([InlineKeyboardButton("🔙 Menu Utama", callback_data="MENU_BACK_MAIN")])

    await query.edit_message_text(
        text=msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def view_ticket_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan kembali gambar E-Tiket / Invoice Resmi kepada user"""
    query = update.callback_query
    await query.answer("Memuat E-Tiket...")
    try:
        res_id = int(query.data.split(":")[1])
        res = database.get_reservation_by_id(res_id)
        if not res:
            await query.message.reply_text("Data reservasi tidak ditemukan.")
            return

        ticket_buf = generate_ticket_invoice(
            booking_code=res["booking_code"],
            user_name=res["user_name"],
            user_phone=res["user_phone"],
            ticket_name=res.get("ticket_name") or "Tiket Wisata Ngrembel",
            visit_date=res["visit_date"],
            ticket_qty=res["ticket_qty"],
            total_price=res.get("payment_amount") or res["total_price"],
            payment_method=res.get("payment_method") or "QRIS Otomatis (Casaku)",
            created_at=res.get("created_at"),
            status="LUNAS / VERIFIED" if res["status"] in ("CONFIRMED", "COMPLETED") else res["status"]
        )

        caption = (
            "🎟 *E-TIKET & INVOICE RESMI WISATA NGREMBEL ASRI* 🎟\n\n"
            f"🔖 *Kode Booking:* `{res['booking_code']}`\n"
            f"👤 *Nama Pemesan:* {res['user_name']}\n"
            f"🎟 *Paket:* {res.get('ticket_name') or 'Tiket Wisata'}\n"
            f"📅 *Tanggal Kunjungan:* {res['visit_date']}\n"
            f"👥 *Jumlah:* {res['ticket_qty']} Orang\n"
            f"💰 *Total Bayar:* {format_rupiah(res.get('payment_amount') or res['total_price'])}\n\n"
            "Status: ✅ *TIKET AKTIF (LUNAS)*\n\n"
            "Tunjukkan gambar e-tiket ini kepada petugas di loket pintu masuk saat tiba di Wisata Ngrembel Asri. Selamat berlibur! 🌿"
        )

        await query.message.reply_photo(
            photo=ticket_buf,
            caption=caption,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error viewing ticket: {e}")
        await query.message.reply_text("Terjadi kesalahan saat memuat e-tiket.")

# --- Conversation: Reservasi Tiket Wisata ---

async def start_reservation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    context.user_data["booking"] = {}
    user = update.effective_user
    context.user_data["booking"]["user_id"] = user.id
    context.user_data["booking"]["default_name"] = user.full_name or user.first_name or "Pengunjung"

    now = datetime.now()
    calendar_markup = create_calendar(now.year, now.month)

    text = (
        "📅 *LANGKAH 1 DARI 5: PILIH TANGGAL KUNJUNGAN*\n\n"
        "Silakan pilih tanggal kedatangan Anda ke Wisata Ngrembel Asri melalui kalender interaktif di bawah:\n"
        "_(Gunakan tombol ◀️ ▶️ untuk mengganti bulan)_"
    )

    if query:
        await query.edit_message_text(
            text=text,
            reply_markup=calendar_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=text,
            reply_markup=calendar_markup,
            parse_mode="Markdown"
        )

    return STATE_SELECT_DATE

async def calendar_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "CAL_IGNORE" or data == "CAL_PAST":
        if data == "CAL_PAST":
            await query.answer("❌ Tanggal ini sudah lewat. Silakan pilih tanggal hari ini atau masa mendatang.", show_alert=True)
        return STATE_SELECT_DATE

    if data.startswith("CAL_NAV:"):
        _, y, m = data.split(":")
        calendar_markup = create_calendar(int(y), int(m))
        text = (
            "📅 *LANGKAH 1 DARI 5: PILIH TANGGAL KUNJUNGAN*\n\n"
            "Silakan pilih tanggal kedatangan Anda ke Wisata Ngrembel Asri melalui kalender di bawah:\n"
            "_(Gunakan tombol ◀️ ▶️ untuk mengganti bulan)_"
        )
        await query.edit_message_text(
            text=text,
            reply_markup=calendar_markup,
            parse_mode="Markdown"
        )
        return STATE_SELECT_DATE

    if data.startswith("CAL_SELECT:"):
        selected_date = data.split(":")[1]
        context.user_data["booking"]["visit_date"] = selected_date
        return await prompt_select_ticket(update, context)

    return STATE_SELECT_DATE

async def prompt_select_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    visit_date = context.user_data["booking"]["visit_date"]
    
    dt = datetime.strptime(visit_date, "%Y-%m-%d")
    formatted_date = f"{dt.day} {MONTH_NAMES_ID[dt.month]} {dt.year}"
    context.user_data["booking"]["formatted_date"] = formatted_date

    tickets = database.get_wisata_list(active_only=True)
    if not tickets:
        await query.edit_message_text(
            text="Mohon maaf, saat ini belum ada tiket aktif yang tersedia.",
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

    keyboard = []
    for t in tickets:
        btn_text = f"🎟 {t['name']} - {format_rupiah(t['price'])}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"SEL_TICKET:{t['id']}")])
    keyboard.append([InlineKeyboardButton("❌ Batalkan Reservasi", callback_data="CANCEL_RESERVATION")])

    text = (
        f"🗓 Tanggal Kunjungan Terpilih: *{formatted_date}*\n\n"
        "🎫 *LANGKAH 2 DARI 5: PILIH PAKET WISATA*\n\n"
        "Silakan pilih jenis tiket atau paket wisata yang ingin Anda pesan:"
    )

    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return STATE_SELECT_TICKET

async def ticket_selected_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    ticket_id = int(query.data.split(":")[1])
    ticket = database.get_wisata_by_id(ticket_id)
    if not ticket:
        await query.edit_message_text("Tiket tidak ditemukan. Silakan pilih kembali.")
        return await prompt_select_ticket(update, context)

    context.user_data["booking"]["ticket_id"] = ticket["id"]
    context.user_data["booking"]["ticket_name"] = ticket["name"]
    context.user_data["booking"]["ticket_price"] = ticket["price"]

    keyboard = [
        [
            InlineKeyboardButton("1 Orang", callback_data="QTY:1"),
            InlineKeyboardButton("2 Orang", callback_data="QTY:2"),
            InlineKeyboardButton("3 Orang", callback_data="QTY:3")
        ],
        [
            InlineKeyboardButton("4 Orang", callback_data="QTY:4"),
            InlineKeyboardButton("5 Orang", callback_data="QTY:5"),
            InlineKeyboardButton("10 Orang", callback_data="QTY:10")
        ],
        [
            InlineKeyboardButton("❌ Batalkan Reservasi", callback_data="CANCEL_RESERVATION")
        ]
    ]

    text = (
        f"🎟 Paket Terpilih: *{ticket['name']}*\n"
        f"💰 Harga: *{format_rupiah(ticket['price'])}* / orang\n\n"
        "👥 *LANGKAH 3 DARI 5: JUMLAH TIKET / ORANG*\n\n"
        "Berapa jumlah orang / tiket yang ingin dipesan?\n"
        "Pilih tombol cepat di bawah atau *ketikkan angka langsung* di chat (contoh: `2`):"
    )

    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return STATE_SELECT_QTY

async def qty_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    qty = int(query.data.split(":")[1])
    context.user_data["booking"]["ticket_qty"] = qty
    return await prompt_contact_name(update, context)

async def qty_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text(
            "⚠️ Harap masukkan angka yang valid (minimal 1 tiket).\nContoh: ketik `2`"
        )
        return STATE_SELECT_QTY

    qty = int(text)
    if qty > 500:
        await update.message.reply_text("Untuk rombongan di atas 500 orang, harap hubungi CS kami langsung.")
        return STATE_SELECT_QTY

    context.user_data["booking"]["ticket_qty"] = qty
    return await prompt_contact_name(update, context)

async def prompt_contact_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    booking = context.user_data["booking"]
    default_name = booking.get("default_name", "Pengunjung")

    keyboard = [
        [InlineKeyboardButton(f"✅ Gunakan: {default_name}", callback_data="NAME_USE_DEFAULT")],
        [InlineKeyboardButton("❌ Batalkan Reservasi", callback_data="CANCEL_RESERVATION")]
    ]

    text = (
        "👤 *LANGKAH 4A: NAMA LENGKAP PEMESAN*\n\n"
        f"Nama pemesan tiket:\n"
        f"Klik tombol di bawah untuk menggunakan nama akun Telegram Anda (*{default_name}*), "
        "atau ketikkan nama lengkap Anda di chat:"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    return STATE_INPUT_NAME

async def name_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["booking"]["user_name"] = context.user_data["booking"]["default_name"]
    return await prompt_contact_phone(update, context)

async def name_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("Nama terlalu pendek. Silakan ketik nama lengkap Anda:")
        return STATE_INPUT_NAME
    context.user_data["booking"]["user_name"] = name
    return await prompt_contact_phone(update, context)

async def prompt_contact_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📱 *LANGKAH 4B: NOMOR WHATSAPP PEMESAN*\n\n"
        "Silakan ketik nomor WhatsApp / HP Anda yang aktif untuk konfirmasi tiket & pengiriman info kedatangan:\n"
        "_(Contoh: `081234567890`)_"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Batalkan", callback_data="CANCEL_RESERVATION")]
            ]),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Batalkan", callback_data="CANCEL_RESERVATION")]
            ]),
            parse_mode="Markdown"
        )
    return STATE_INPUT_PHONE

async def phone_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    cleaned = "".join(filter(str.isdigit, phone))
    if len(cleaned) < 9 or len(cleaned) > 15:
        await update.message.reply_text(
            "⚠️ Nomor telepon tidak valid. Pastikan nomor terdiri dari 9-15 digit angka.\nContoh: `081234567890`"
        )
        return STATE_INPUT_PHONE

    context.user_data["booking"]["user_phone"] = phone
    return await show_booking_confirmation(update, context)

async def show_booking_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    booking = context.user_data["booking"]
    total = booking["ticket_price"] * booking["ticket_qty"]
    booking["total_price"] = total

    text = (
        "📋 *LANGKAH 5: KONFIRMASI RINGKASAN RESERVASI*\n\n"
        "Mohon periksa kembali detail pemesanan tiket Anda:\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷 *Paket Wisata:* {booking['ticket_name']}\n"
        f"📅 *Tanggal Kunjungan:* {booking['formatted_date']}\n"
        f"👥 *Jumlah Orang:* {booking['ticket_qty']} Orang\n"
        f"💵 *Harga Satuan:* {format_rupiah(booking['ticket_price'])}\n"
        f"💰 *TOTAL HARGA:* *{format_rupiah(total)}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Nama Pemesan:* {booking['user_name']}\n"
        f"📱 *No. WhatsApp:* {booking['user_phone']}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Apakah data di atas sudah benar? Klik tombol di bawah untuk membuat QRIS pembayaran otomatis:"
    )

    keyboard = [
        [InlineKeyboardButton("💳 Bayar via QRIS Otomatis", callback_data="CONFIRM_PAYMENT")],
        [InlineKeyboardButton("❌ Batalkan Reservasi", callback_data="CANCEL_RESERVATION")]
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    return STATE_CONFIRM_BOOKING

async def watch_casaku_payment(
    bot,
    chat_id: int,
    trx_id: str,
    res_id: int,
    booking_code: str,
    ticket_name: str,
    qty: int,
    visit_date: str,
    total_amount: int
):
    """
    Background worker untuk memantau status pembayaran Casaku setiap 7 detik
    secara otomatis tanpa mengharuskan pengguna menekan tombol cek status.
    """
    for _ in range(85): # ~10 menit
        await asyncio.sleep(7)
        curr_res = database.get_reservation_by_id(res_id)
        if not curr_res or curr_res["status"] in ("CONFIRMED", "COMPLETED", "REJECTED"):
            return

        status_res = casaku.check_status(trx_id)
        if status_res.get("success") and status_res.get("status") == "paid":
            database.update_reservation_status(res_id, "CONFIRMED", "Lunas otomatis via QRIS Casaku")
            
            # Generate gambar E-Tiket / Invoice Resmi
            ticket_buf = generate_ticket_invoice(
                booking_code=booking_code,
                user_name=curr_res.get("user_name", "Pengunjung"),
                user_phone=curr_res.get("user_phone", "-"),
                ticket_name=ticket_name,
                visit_date=visit_date,
                ticket_qty=qty,
                total_price=total_amount,
                payment_method="QRIS Otomatis (Casaku)",
                created_at=curr_res.get("created_at")
            )

            success_msg = (
                "🎉 *PEMBAYARAN QRIS BERHASIL DITERIMA!* 🎉\n\n"
                f"🔖 *Kode Booking:* `{booking_code}`\n"
                f"🎟 *Paket:* {ticket_name}\n"
                f"📅 *Tanggal Kunjungan:* {visit_date}\n"
                f"👥 *Jumlah:* {qty} Orang\n"
                f"💰 *Total Bayar:* {format_rupiah(total_amount)}\n\n"
                "Status: ✅ *TIKET RESMI AKTIF & DIKONFIRMASI*\n\n"
                "Simpan gambar E-Tiket / Invoice di atas dan tunjukkan kepada petugas di loket pintu masuk saat tiba di Wisata Ngrembel Asri. "
                "Selamat berlibur dan menikmati keindahan alam bersama keluarga! 🌿"
            )
            try:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=ticket_buf,
                    caption=success_msg,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔍 Cek Status Reservasi", callback_data="MENU_CHECK_STATUS")],
                        [InlineKeyboardButton("🔙 Menu Utama", callback_data="MENU_BACK_MAIN")]
                    ])
                )
            except Exception as e:
                logger.error(f"Gagal mengirim notif otomatis ke user: {e}")
            return
        elif status_res.get("status") in ("cancel", "expired"):
            database.update_reservation_status(res_id, "REJECTED", "Kedaluwarsa via Casaku")
            return

async def confirm_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    booking = context.user_data["booking"]
    booking_code = generate_booking_code()
    booking["booking_code"] = booking_code

    total_base_price = booking["total_price"]

    # Simpan record awal ke SQLite database
    res_id = database.create_reservation(
        booking_code=booking_code,
        user_id=booking["user_id"],
        user_name=booking["user_name"],
        user_phone=booking["user_phone"],
        ticket_id=booking["ticket_id"],
        visit_date=booking["visit_date"],
        ticket_qty=booking["ticket_qty"],
        total_price=total_base_price
    )
    booking["reservation_id"] = res_id

    # 1. Coba Generate QRIS melalui API Casaku
    casaku_res = casaku.generate_qris(
        amount=total_base_price,
        prefix="NGR"
    )

    if casaku_res.get("success"):
        trx_id = casaku_res["transaction_id"]
        total_amount = casaku_res["total_amount"] # Nominal dengan kode unik
        qr_string = casaku_res["qr_string"]

        booking["casaku_trx_id"] = trx_id
        booking["payment_amount"] = total_amount

        # Update database record
        database.update_reservation_casaku(res_id, trx_id, qr_string, total_amount)

        # Buat gambar QRIS dari qr_string
        qr_buf = casaku.generate_qr_image_bytes(qr_string)

        caption = (
            "📲 *PEMBAYARAN QRIS OTOMATIS (CASAKU)* 📲\n\n"
            f"🔖 *Kode Booking:* `{booking_code}`\n"
            f"💰 *TOTAL YANG HARUS DIBAYAR:*\n"
            f"👉 *{format_rupiah(total_amount)}* 👈\n"
            "⚠️ _Harap transfer TEPAT hingga digit terakhir agar otomatis terverifikasi!_\n\n"
            "📱 *Bisa di-scan menggunakan:*\n"
            "• DANA, GoPay, OVO, ShopeePay, LinkAja\n"
            "• BCA, Mandiri, BRI, BNI, dan semua Mobile Banking\n\n"
            "⏳ *Masa Berlaku QRIS:* 15 Menit\n"
            "⚡️ *Sistem akan mendeteksi pembayaran secara OTOMATIS tanpa perlu kirim bukti transfer.*"
        )

        keyboard = [
            [InlineKeyboardButton("🔄 Cek Status Pembayaran", callback_data=f"CHECK_CASAKU:{trx_id}")],
            [InlineKeyboardButton("📸 Upload Bukti Manual (Opsional)", callback_data="MANUAL_UPLOAD_PROOF")],
            [InlineKeyboardButton("❌ Batalkan Reservasi", callback_data="CANCEL_RESERVATION")]
        ]

        # Kirim QR code gambar
        await query.message.reply_photo(
            photo=qr_buf,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # Hapus pesan teks ringkasan sebelumnya agar rapi
        try:
            await query.message.delete()
        except Exception:
            pass

        # Jalankan background watcher otomatis
        asyncio.create_task(
            watch_casaku_payment(
                bot=context.bot,
                chat_id=update.effective_chat.id,
                trx_id=trx_id,
                res_id=res_id,
                booking_code=booking_code,
                ticket_name=booking["ticket_name"],
                qty=booking["ticket_qty"],
                visit_date=booking["formatted_date"],
                total_amount=total_amount
            )
        )
        return STATE_WAIT_PAYMENT_PROOF

    else:
        # Fallback jika Casaku belum dikonfigurasi atau sedang ada kendala
        err_msg = casaku_res.get("error", "Koneksi gateway tidak tersedia")
        settings = database.get_settings()
        bank_info = settings.get("bank_info", "Bank BCA: 1234567890 a.n. Ngrembel Asri Wisata")

        fallback_text = (
            "💳 *INSTRUKSI PEMBAYARAN TIKET* 💳\n\n"
            f"🔖 *Kode Booking Anda:* `{booking_code}`\n"
            f"💰 *Total Bayar:* *{format_rupiah(total_base_price)}*\n\n"
            f"⚠️ _{err_msg}_\n\n"
            "Silakan transfer manual ke rekening resmi kami:\n"
            f"{bank_info}\n\n"
            "📸 *Setelah transfer:*\n"
            "Kirimkan foto/screenshot bukti transfer di chat ini untuk diverifikasi admin."
        )

        keyboard = [
            [InlineKeyboardButton("✅ Sudah Transfer (Verifikasi Nanti)", callback_data="DONE_TRANSFER_LATER")],
            [InlineKeyboardButton("❌ Batalkan Reservasi", callback_data="CANCEL_RESERVATION")]
        ]

        await query.edit_message_text(
            text=fallback_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return STATE_WAIT_PAYMENT_PROOF

async def check_casaku_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    trx_id = query.data.split(":", 1)[1] if ":" in query.data else None

    if not trx_id:
        await query.answer("ID Transaksi tidak ditemukan.", show_alert=True)
        return STATE_WAIT_PAYMENT_PROOF

    status_res = casaku.check_status(trx_id)
    if not status_res.get("success"):
        await query.answer(f"Gagal memeriksa status: {status_res.get('error', 'Koneksi error')}", show_alert=True)
        return STATE_WAIT_PAYMENT_PROOF

    st = status_res.get("status")
    if st == "paid":
        res = database.get_reservation_by_casaku_trx(trx_id)
        if res:
            database.update_reservation_status(res["id"], "CONFIRMED", "Lunas via QRIS Casaku")
            booking_code = res["booking_code"]
            ticket_name = res["ticket_name"]
            visit_date = res["visit_date"]
            qty = res["ticket_qty"]
            total_amount = res["payment_amount"] or res["total_price"]
        else:
            booking_code = "NGR-XXXX"
            ticket_name = "Tiket Wisata"
            visit_date = "-"
            qty = 1
            total_amount = 0

        await query.answer("✅ Pembayaran Anda telah terverifikasi lunas!", show_alert=True)

        # Generate gambar E-Tiket / Invoice Resmi
        ticket_buf = generate_ticket_invoice(
            booking_code=booking_code,
            user_name=res.get("user_name", "Pengunjung"),
            user_phone=res.get("user_phone", "-"),
            ticket_name=ticket_name,
            visit_date=visit_date,
            ticket_qty=qty,
            total_price=total_amount,
            payment_method="QRIS Otomatis (Casaku)",
            created_at=res.get("created_at")
        )

        success_msg = (
            "🎉 *PEMBAYARAN QRIS BERHASIL DIVERIFIKASI!* 🎉\n\n"
            f"🔖 *Kode Booking:* `{booking_code}`\n"
            f"🎟 *Paket:* {ticket_name}\n"
            f"📅 *Tanggal Kunjungan:* {visit_date}\n"
            f"👥 *Jumlah:* {qty} Orang\n"
            f"💰 *Total Bayar:* {format_rupiah(total_amount)}\n\n"
            "Status: ✅ *TIKET RESMI AKTIF & DIKONFIRMASI*\n\n"
            "Simpan gambar E-Tiket di atas dan tunjukkan kepada petugas di loket pintu masuk saat tiba di lokasi. "
            "Selamat berlibur di Wisata Ngrembel Asri Semarang! 🌿"
        )

        await query.message.reply_photo(
            photo=ticket_buf,
            caption=success_msg,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Cek Status Reservasi", callback_data="MENU_CHECK_STATUS")],
                [InlineKeyboardButton("🔙 Menu Utama", callback_data="MENU_BACK_MAIN")]
            ]),
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return ConversationHandler.END

    elif st == "pending":
        await query.answer(
            "⏳ Pembayaran belum terdeteksi di sistem Casaku.\n\n"
            "Pastikan Anda telah mentransfer jumlah yang tepat melalui m-banking atau e-wallet (DANA, GoPay, OVO, ShopeePay, dll).",
            show_alert=True
        )
        return STATE_WAIT_PAYMENT_PROOF

    elif st in ("expired", "cancel"):
        await query.answer("❌ Transaksi telah kedaluwarsa atau dibatalkan.", show_alert=True)
        await query.message.reply_text(
            "❌ *Waktu pembayaran QRIS telah kedaluwarsa.* Silakan buat reservasi baru.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return ConversationHandler.END

    else:
        await query.answer(f"Status transaksi: {st.upper()}", show_alert=True)
        return STATE_WAIT_PAYMENT_PROOF

async def prompt_manual_upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "📸 *UPLOAD BUKTI TRANSFER MANUAL*\n\n"
        "Silakan kirimkan foto atau screenshot bukti transfer Anda di chat ini.\n"
        "Petugas admin kami akan memverifikasi bukti Anda secara manual."
    )
    await query.message.reply_text(text, parse_mode="Markdown")
    return STATE_WAIT_PAYMENT_PROOF

async def handle_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    booking = context.user_data.get("booking", {})
    booking_code = booking.get("booking_code")
    res_id = booking.get("reservation_id")

    if not booking_code or not res_id:
        await update.message.reply_text("Sesi reservasi telah berakhir. Silakan gunakan /start.")
        return ConversationHandler.END

    photo = update.message.photo[-1]
    file_obj = await photo.get_file()
    filename = f"{booking_code}_proof.jpg"
    dest_path = UPLOAD_DIR / filename
    await file_obj.download_to_drive(str(dest_path))

    conn = database.get_db()
    conn.execute(
        "UPDATE reservations SET payment_proof = ?, status = 'PAID' WHERE id = ?",
        (filename, res_id)
    )
    conn.commit()
    conn.close()

    text = (
        "🎉 *BUKTI PEMBAYARAN BERHASIL DITERIMA!* 🎉\n\n"
        f"🔖 *Kode Booking:* `{booking_code}`\n"
        f"🎟 *Paket:* {booking['ticket_name']}\n"
        f"📅 *Tanggal Kunjungan:* {booking['formatted_date']}\n"
        f"👥 *Jumlah Tiket:* {booking['ticket_qty']} Orang\n"
        f"💰 *Total:* {format_rupiah(booking.get('payment_amount') or booking['total_price'])}\n\n"
        "Status: ⏳ *PEMBAYARAN DITERIMA - MENUNGGU VERIFIKASI ADMIN*\n\n"
        "Admin kami akan segera memverifikasi bukti Anda. Tunjukkan kode booking ini saat berkunjung. Terima kasih! 🌿"
    )

    await update.message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Cek Status Reservasi", callback_data="MENU_CHECK_STATUS")],
            [InlineKeyboardButton("🔙 Menu Utama", callback_data="MENU_BACK_MAIN")]
        ]),
        parse_mode="Markdown"
    )
    context.user_data.clear()
    return ConversationHandler.END

async def done_transfer_later_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    booking = context.user_data.get("booking", {})
    booking_code = booking.get("booking_code", "NGR-XXXX")

    text = (
        "✅ *RESERVASI TELAH TERCATAT!* ✅\n\n"
        f"🔖 *Kode Booking:* `{booking_code}`\n"
        "Status: ⏳ *Menunggu Pembayaran*\n\n"
        "Segera selesaikan pembayaran Anda sebelum hari kunjungan. "
        "Anda dapat memeriksa status pemesanan kapan saja melalui menu *Cek Reservasi*.\n\n"
        "Terima kasih dan sampai jumpa di Wisata Ngrembel Asri Semarang! 🌿"
    )

    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Cek Status Reservasi", callback_data="MENU_CHECK_STATUS")],
            [InlineKeyboardButton("🔙 Menu Utama", callback_data="MENU_BACK_MAIN")]
        ]),
        parse_mode="Markdown"
    )
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_reservation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    text = "❌ *Reservasi telah dibatalkan.*\n\nSilakan pilih menu di bawah jika ingin mencari info atau membuat reservasi baru:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    return ConversationHandler.END

_telegram_bot_app = None

def get_bot_app():
    global _telegram_bot_app
    return _telegram_bot_app

async def send_customer_notification(user_id: int, message: str, photo: io.BytesIO = None, reply_markup=None) -> bool:
    """Mengirim pesan notifikasi atau foto E-Tiket dari web admin ke Telegram user"""
    global _telegram_bot_app
    if not _telegram_bot_app or not BOT_TOKEN:
        return False
    try:
        if photo:
            await _telegram_bot_app.bot.send_photo(
                chat_id=user_id,
                photo=photo,
                caption=message,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await _telegram_bot_app.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        return True
    except Exception as e:
        logger.error(f"Gagal mengirim notifikasi Telegram ke user {user_id}: {e}")
        return False

def build_application():
    global _telegram_bot_app
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN belum diset di .env! Bot Telegram tidak dapat dijalankan.")
        return None

    app = Application.builder().token(BOT_TOKEN).build()
    _telegram_bot_app = app

    reservation_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_reservation, pattern="^MENU_RESERVATION$"),
            CommandHandler("reservasi", start_reservation)
        ],
        states={
            STATE_SELECT_DATE: [
                CallbackQueryHandler(calendar_callback_handler, pattern="^(CAL_NAV:|CAL_SELECT:|CAL_IGNORE|CAL_PAST)")
            ],
            STATE_SELECT_TICKET: [
                CallbackQueryHandler(ticket_selected_handler, pattern="^SEL_TICKET:")
            ],
            STATE_SELECT_QTY: [
                CallbackQueryHandler(qty_button_handler, pattern="^QTY:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, qty_text_handler)
            ],
            STATE_INPUT_NAME: [
                CallbackQueryHandler(name_button_handler, pattern="^NAME_USE_DEFAULT$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, name_text_handler)
            ],
            STATE_INPUT_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, phone_text_handler)
            ],
            STATE_CONFIRM_BOOKING: [
                CallbackQueryHandler(confirm_payment_handler, pattern="^CONFIRM_PAYMENT$")
            ],
            STATE_WAIT_PAYMENT_PROOF: [
                CallbackQueryHandler(check_casaku_callback_handler, pattern="^CHECK_CASAKU:"),
                CallbackQueryHandler(prompt_manual_upload_handler, pattern="^MANUAL_UPLOAD_PROOF$"),
                MessageHandler(filters.PHOTO, handle_payment_proof),
                CallbackQueryHandler(done_transfer_later_handler, pattern="^DONE_TRANSFER_LATER$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_reservation, pattern="^CANCEL_RESERVATION$"),
            CommandHandler("cancel", cancel_reservation)
        ],
        allow_reentry=True,
        per_message=False
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(reservation_conv)
    app.add_handler(CallbackQueryHandler(start_command, pattern="^MENU_BACK_MAIN$"))
    app.add_handler(CallbackQueryHandler(show_prices, pattern="^MENU_PRICES$"))
    app.add_handler(CallbackQueryHandler(show_hours, pattern="^MENU_HOURS$"))
    app.add_handler(CallbackQueryHandler(show_location, pattern="^MENU_LOCATION$"))
    app.add_handler(CallbackQueryHandler(show_contact, pattern="^MENU_CONTACT$"))
    app.add_handler(CallbackQueryHandler(check_reservation_status, pattern="^MENU_CHECK_STATUS$"))
    app.add_handler(CallbackQueryHandler(view_ticket_callback_handler, pattern="^VIEW_TICKET:"))

    return app

import calendar
from datetime import datetime, date
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

MONTH_NAMES_ID = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

DAY_NAMES_ID = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]

def create_calendar(year: int = None, month: int = None) -> InlineKeyboardMarkup:
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    keyboard = []

    # Baris 1: Navigasi Bulan & Tahun
    month_name = MONTH_NAMES_ID[month]
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1

    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    header_buttons = [
        InlineKeyboardButton("◀️", callback_data=f"CAL_NAV:{prev_year}:{prev_month}"),
        InlineKeyboardButton(f"🗓 {month_name} {year}", callback_data="CAL_IGNORE"),
        InlineKeyboardButton("▶️", callback_data=f"CAL_NAV:{next_year}:{next_month}")
    ]
    keyboard.append(header_buttons)

    # Baris 2: Nama-nama Hari
    day_headers = [InlineKeyboardButton(d, callback_data="CAL_IGNORE") for d in DAY_NAMES_ID]
    keyboard.append(day_headers)

    # Baris 3+: Tanggal-tanggal dalam bulan
    cal = calendar.monthcalendar(year, month)
    today = date.today()

    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="CAL_IGNORE"))
            else:
                current_date = date(year, month, day)
                if current_date < today:
                    # Tanggal masa lalu tidak bisa dipilih
                    row.append(InlineKeyboardButton(f"·{day}·", callback_data="CAL_PAST"))
                else:
                    date_str = current_date.strftime("%Y-%m-%d")
                    # Berikan indikator khusus untuk hari ini
                    label = f"📍{day}" if current_date == today else str(day)
                    row.append(InlineKeyboardButton(label, callback_data=f"CAL_SELECT:{date_str}"))
        keyboard.append(row)

    # Baris Bawah: Tombol Batal
    keyboard.append([
        InlineKeyboardButton("❌ Batalkan Reservasi", callback_data="CANCEL_RESERVATION")
    ])

    return InlineKeyboardMarkup(keyboard)

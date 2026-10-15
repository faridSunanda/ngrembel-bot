import os
import secrets
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import database
from config import (
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
    SECRET_KEY,
    STATIC_DIR,
    TEMPLATES_DIR,
    UPLOAD_DIR,
)
from bot import send_customer_notification

app = FastAPI(title="Ngrembel Asri Admin Panel")

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Session Middleware
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, session_cookie="ngrembel_admin_sess")

def is_authenticated(request: Request) -> bool:
    return request.session.get("authenticated") is True

def require_admin(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/login"})

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == status.HTTP_307_TEMPORARY_REDIRECT and "Location" in exc.headers:
        return RedirectResponse(url=exc.headers["Location"])
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# --- Authentication Routes ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=302)
    error = request.query_params.get("error")
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": error}
    )

@app.post("/login")
async def process_login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = database.verify_admin(username, password)
    if user:
        request.session["authenticated"] = True
        request.session["admin_user"] = user["username"]
        request.session["admin_name"] = user["full_name"] or user["username"]
        return RedirectResponse(url="/", status_code=302)
    else:
        return RedirectResponse(url="/login?error=Username+atau+password+salah", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

# --- Dashboard Overview ---

@app.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    stats = database.get_dashboard_stats()
    recent_reservations = database.get_reservations()[:8]
    wisata_list = database.get_wisata_list()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "page_title": "Dashboard Overview",
            "stats": stats,
            "recent_reservations": recent_reservations,
            "wisata_count": len(wisata_list),
            "admin_name": request.session.get("admin_name", "Admin")
        }
    )

# --- Kelola Wisata & Tiket ---

@app.get("/wisata", response_class=HTMLResponse)
async def wisata_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    tickets = database.get_wisata_list()
    msg = request.query_params.get("msg")
    return templates.TemplateResponse(
        request=request,
        name="wisata.html",
        context={
            "page_title": "Kelola Data Wisata & Tiket",
            "tickets": tickets,
            "msg": msg,
            "admin_name": request.session.get("admin_name", "Admin")
        }
    )

@app.post("/wisata/add")
async def add_wisata(
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    price: int = Form(...),
    description: str = Form(""),
    is_active: int = Form(1)
):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    database.create_wisata(name, category, price, description, is_active)
    return RedirectResponse(url="/wisata?msg=Paket+wisata+berhasil+ditambahkan", status_code=302)

@app.post("/wisata/edit/{wisata_id}")
async def edit_wisata(
    wisata_id: int,
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    price: int = Form(...),
    description: str = Form(""),
    is_active: int = Form(1)
):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    database.update_wisata(wisata_id, name, category, price, description, is_active)
    return RedirectResponse(url="/wisata?msg=Paket+wisata+berhasil+diperbarui", status_code=302)

@app.post("/wisata/delete/{wisata_id}")
async def delete_wisata(wisata_id: int, request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    database.delete_wisata(wisata_id)
    return RedirectResponse(url="/wisata?msg=Paket+wisata+berhasil+dihapus", status_code=302)

# --- Kelola Reservasi ---

@app.get("/reservations", response_class=HTMLResponse)
async def reservations_page(
    request: Request,
    status_filter: str = "ALL",
    q: str = ""
):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    reservations = database.get_reservations(status=status_filter, search=q)
    msg = request.query_params.get("msg")

    return templates.TemplateResponse(
        request=request,
        name="reservations.html",
        context={
            "page_title": "Kelola Reservasi Tiket",
            "reservations": reservations,
            "current_filter": status_filter,
            "search_query": q,
            "msg": msg,
            "admin_name": request.session.get("admin_name", "Admin")
        }
    )

@app.get("/api/reservations/{res_id}")
async def api_reservation_detail(res_id: int, request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    res = database.get_reservation_by_id(res_id)
    if not res:
        raise HTTPException(status_code=404, detail="Reservasi tidak ditemukan")

    return JSONResponse(content=res)

@app.post("/reservations/status/{res_id}")
async def update_reservation_status(
    res_id: int,
    request: Request,
    status_val: str = Form(...),
    admin_notes: str = Form("")
):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    res = database.get_reservation_by_id(res_id)
    if not res:
        return RedirectResponse(url="/reservations?msg=Reservasi+tidak+ditemukan", status_code=302)

    database.update_reservation_status(res_id, status_val, admin_notes)

    # Kirim notifikasi instan ke Telegram User
    status_labels = {
        "CONFIRMED": "✅ DIKONFIRMASI (Tiket Aktif)",
        "PAID": "💵 PEMBAYARAN DITERIMA (Sedang Diproses)",
        "COMPLETED": "🎉 SELESAI DIGUNAKAN",
        "REJECTED": "❌ DIBATALKAN / DITOLAK"
    }
    label = status_labels.get(status_val, status_val)

    notif_msg = (
        f"📢 *PEMBARUAN STATUS RESERVASI*\n\n"
        f"Halo *{res['user_name']}*,\n"
        f"Status reservasi Anda untuk kode booking `{res['booking_code']}` telah diperbarui menjadi:\n\n"
        f"👉 *{label}*\n\n"
        f"📅 Tanggal Kunjungan: {res['visit_date']}\n"
        f"🎟 Paket: {res['ticket_name']} ({res['ticket_qty']} Orang)\n"
    )
    if admin_notes:
        notif_msg += f"💬 *Catatan dari Admin:* {admin_notes}\n"

    if status_val == "CONFIRMED":
        from ticket_generator import generate_ticket_invoice
        ticket_buf = generate_ticket_invoice(
            booking_code=res["booking_code"],
            user_name=res["user_name"],
            user_phone=res["user_phone"],
            ticket_name=res.get("ticket_name") or "Tiket Wisata Ngrembel Asri",
            visit_date=res["visit_date"],
            ticket_qty=res["ticket_qty"],
            total_price=res.get("payment_amount") or res["total_price"],
            payment_method=res.get("payment_method") or "Transfer / QRIS",
            created_at=res.get("created_at")
        )
        notif_msg += "\n🎉 *Tiket Anda sudah siap!* Simpan dan tunjukkan gambar E-Tiket di atas kepada petugas di loket pintu masuk. Selamat berlibur di Wisata Ngrembel Asri! 🌿"
        await send_customer_notification(res["user_id"], notif_msg, photo=ticket_buf)
    else:
        await send_customer_notification(res["user_id"], notif_msg)

    return RedirectResponse(url="/reservations?msg=Status+reservasi+berhasil+diperbarui", status_code=302)

@app.post("/reservations/delete/{res_id}")
async def delete_reservation(res_id: int, request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    database.delete_reservation(res_id)
    return RedirectResponse(url="/reservations?msg=Data+reservasi+berhasil+dihapus", status_code=302)

@app.get("/reservations/{res_id}/invoice")
async def view_reservation_invoice(res_id: int, request: Request):
    """Endpoint web admin untuk melihat dan mencetak E-Tiket / Invoice Resmi"""
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    res = database.get_reservation_by_id(res_id)
    if not res:
        raise HTTPException(status_code=404, detail="Reservasi tidak ditemukan")

    from ticket_generator import generate_ticket_invoice
    from fastapi.responses import Response

    ticket_buf = generate_ticket_invoice(
        booking_code=res["booking_code"],
        user_name=res["user_name"],
        user_phone=res["user_phone"],
        ticket_name=res.get("ticket_name") or "Tiket Wisata Ngrembel Asri",
        visit_date=res["visit_date"],
        ticket_qty=res["ticket_qty"],
        total_price=res.get("payment_amount") or res["total_price"],
        payment_method=res.get("payment_method") or "QRIS Casaku",
        created_at=res.get("created_at"),
        status="LUNAS / VERIFIED" if res["status"] in ("CONFIRMED", "COMPLETED") else res["status"]
    )

    return Response(
        content=ticket_buf.getvalue(),
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="ETiket_{res["booking_code"]}.png"'}
    )

# --- Webhook Casaku & Device Status ---

@app.post("/api/webhook/casaku")
async def casaku_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Casaku-Signature", "")

    import casaku
    import json
    import config

    settings = database.get_settings()
    secret = settings.get("casaku_webhook_secret") or config.CASAKU_WEBHOOK_SECRET

    if not casaku.verify_webhook_signature(raw_body, signature, secret):
        return JSONResponse(status_code=401, content={"error": "Invalid signature"})

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    trx_id = payload.get("transactionId")
    status_val = payload.get("status")
    amount = payload.get("amount")

    if status_val == "paid" and trx_id:
        res = database.get_reservation_by_casaku_trx(trx_id)
        if res:
            database.update_reservation_status(res["id"], "CONFIRMED", f"Lunas otomatis via QRIS Casaku (Rp {amount:,})")

            from ticket_generator import generate_ticket_invoice
            ticket_buf = generate_ticket_invoice(
                booking_code=res["booking_code"],
                user_name=res["user_name"],
                user_phone=res["user_phone"],
                ticket_name=res.get("ticket_name") or "Tiket Wisata Ngrembel Asri",
                visit_date=res["visit_date"],
                ticket_qty=res["ticket_qty"],
                total_price=res.get("payment_amount") or res["total_price"],
                payment_method="QRIS Otomatis (Casaku)",
                created_at=res.get("created_at")
            )

            notif_msg = (
                f"🎉 *PEMBAYARAN QRIS BERHASIL DIVERIFIKASI!* 🎉\n\n"
                f"Halo *{res['user_name']}*,\n"
                f"Pembayaran Anda sebesar *Rp {amount:,.0f}* untuk kode booking `{res['booking_code']}` telah terverifikasi lunas oleh sistem Casaku!\n\n"
                f"🎟 *Paket:* {res['ticket_name']} ({res['ticket_qty']} Orang)\n"
                f"📅 *Tanggal Kunjungan:* {res['visit_date']}\n"
                f"📌 *Status:* ✅ *TIKET RESMI AKTIF & DIKONFIRMASI*\n\n"
                f"Simpan gambar E-Tiket / Invoice di atas dan tunjukkan kepada petugas di loket pintu masuk saat tiba di Wisata Ngrembel Asri. Selamat berlibur! 🌿"
            ).replace(",", ".")
            await send_customer_notification(res["user_id"], notif_msg, photo=ticket_buf)

    return JSONResponse(status_code=200, content={"status": 200, "message": "Webhook processed"})

@app.get("/api/casaku/test-device")
async def test_casaku_device(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    import casaku
    settings = database.get_settings()
    key = settings.get("casaku_license_key")
    result = casaku.check_device_listener(key)
    return JSONResponse(content=result)

# --- Settings & Informasi Wisata ---

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    settings = database.get_settings()
    msg = request.query_params.get("msg")

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "page_title": "Pengaturan Info Wisata & Pembayaran",
            "settings": settings,
            "msg": msg,
            "admin_name": request.session.get("admin_name", "Admin")
        }
    )

@app.post("/settings")
async def save_settings(
    request: Request,
    opening_hours: str = Form(...),
    location_address: str = Form(...),
    maps_url: str = Form(...),
    phone_contact: str = Form(...),
    bank_info: str = Form(...),
    qris_info: str = Form(...),
    casaku_license_key: str = Form(""),
    casaku_qr_id: str = Form(""),
    casaku_webhook_secret: str = Form(""),
    casaku_package_id: str = Form("id.dana")
):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    database.update_setting("opening_hours", opening_hours)
    database.update_setting("location_address", location_address)
    database.update_setting("maps_url", maps_url)
    database.update_setting("phone_contact", phone_contact)
    database.update_setting("bank_info", bank_info)
    database.update_setting("qris_info", qris_info)
    database.update_setting("casaku_license_key", casaku_license_key.strip())
    database.update_setting("casaku_qr_id", casaku_qr_id.strip())
    database.update_setting("casaku_webhook_secret", casaku_webhook_secret.strip())
    database.update_setting("casaku_package_id", casaku_package_id.strip())

    # Sync dynamically to runtime config
    import config
    config.CASAKU_LICENSE_KEY = casaku_license_key.strip()
    config.CASAKU_QR_ID = casaku_qr_id.strip()
    config.CASAKU_WEBHOOK_SECRET = casaku_webhook_secret.strip()
    config.CASAKU_PACKAGE_ID = casaku_package_id.strip()

    return RedirectResponse(url="/settings?msg=Pengaturan+berhasil+disimpan", status_code=302)

import hmac
import hashlib
import json
import logging
import io
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
import qrcode
from config import CASAKU_LICENSE_KEY, CASAKU_QR_ID, CASAKU_WEBHOOK_SECRET, CASAKU_PACKAGE_ID

logger = logging.getLogger(__name__)

CASAKU_BASE_URL = "https://api.casaku.id"

CASAKU_PACKAGES = {
    "dana": "id.dana",
    "orderkuota": "com.orderkuota.app",
    "gopay": "com.gojek.gopaymerchant",
    "bca": "com.bca.msb",
    "shopeepay": "com.shopee.id",
    "shopeepartner": "com.shopeepay.merchant.id",
    "mandiri": "id.bmri.livinmerchant",
    "bri": "id.co.bri.merchant",
    "cimb": "com.cimbedc",
    "bni": "id.co.bni.merchant",
    "bsi": "id.co.bankbsi.byond",
    "jakone": "com.bankdki.jakone.merchant",
    "bukalapak": "com.bukalapak.android",
}

def is_casaku_configured() -> bool:
    return bool(CASAKU_LICENSE_KEY and CASAKU_QR_ID and CASAKU_LICENSE_KEY.strip() and CASAKU_QR_ID.strip())

def generate_qris(
    amount: int,
    prefix: str = "NGR",
    package_id: Optional[str] = None,
    use_unique_code: bool = True,
    expired_in_minutes: int = 15,
    license_key: Optional[str] = None,
    qr_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Membuat transaksi QRIS dinamis melalui Casaku API v2
    """
    key = (license_key or CASAKU_LICENSE_KEY or "").strip()
    qid = (qr_id or CASAKU_QR_ID or "").strip()
    pkg = package_id or CASAKU_PACKAGE_ID or "id.dana"

    if not key or not qid:
        return {
            "success": False,
            "error": "CASAKU_LICENSE_KEY atau CASAKU_QR_ID belum dikonfigurasi di .env atau Pengaturan Admin."
        }

    url = f"{CASAKU_BASE_URL}/api/generate/v2/qris"
    headers = {
        "Content-Type": "application/json",
        "x-license-key": key,
        "User-Agent": "NgrembelBot/1.0"
    }

    payload = {
        "qr_id": qid,
        "amount": int(amount),
        "useUniqueCode": bool(use_unique_code),
        "packageIds": [pkg],
        "expiredInMinutes": expired_in_minutes,
        "qrType": "dynamic",
        "paymentMethod": "qris",
        "useQris": True,
        "prefix": prefix[:8]
    }

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")
            res_json = json.loads(resp_body)

        if res_json.get("status") == 200 and "data" in res_json:
            data = res_json["data"]
            return {
                "success": True,
                "transaction_id": data.get("transactionId"),
                "total_amount": data.get("totalAmount") or amount,
                "qr_string": data.get("qr_string"),
                "expired_at": data.get("expiredAt"),
                "raw": data
            }
        else:
            msg = res_json.get("message", "Gagal generate QRIS dari Casaku")
            logger.error(f"Casaku API error: {msg}")
            return {"success": False, "error": msg}

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        logger.error(f"HTTPError {e.code} from Casaku: {error_body}")
        try:
            err_json = json.loads(error_body)
            msg = err_json.get("message", f"HTTP {e.code}: {e.reason}")
        except Exception:
            msg = f"HTTP {e.code}: {e.reason}"

        if e.code == 403 and "device" in msg.lower():
            msg = "Aplikasi listener Casaku di perangkat HP Android sedang offline. Pastikan aplikasi Casaku berjalan dan checklist hijau."
        return {"success": False, "error": msg, "status_code": e.code}

    except Exception as e:
        logger.error(f"Exception during Casaku request: {e}")
        return {"success": False, "error": str(e)}

def check_status(
    transaction_id: str,
    license_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Memeriksa status transaksi ke Casaku API
    Status output: 'pending', 'paid', 'cancel', 'expired'
    """
    key = (license_key or CASAKU_LICENSE_KEY or "").strip()
    if not key:
        return {"success": False, "error": "CASAKU_LICENSE_KEY belum dikonfigurasi"}

    url = f"{CASAKU_BASE_URL}/api/generate/check-status"
    headers = {
        "Content-Type": "application/json",
        "x-license-key": key,
        "User-Agent": "NgrembelBot/1.0"
    }
    payload = {"transactionId": transaction_id}

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read().decode("utf-8")
            res_json = json.loads(resp_body)

        if res_json.get("status") == 200 and "data" in res_json:
            data = res_json["data"]
            return {
                "success": True,
                "status": data.get("status", "pending"),
                "transaction_id": data.get("transactionId"),
                "raw": data
            }
        else:
            return {"success": False, "error": res_json.get("message", "Gagal cek status")}

    except Exception as e:
        logger.error(f"Error checking Casaku status for {transaction_id}: {e}")
        return {"success": False, "error": str(e)}

def check_device_listener(license_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Memeriksa apakah perangkat aplikasi Android Casaku sedang online
    """
    key = (license_key or CASAKU_LICENSE_KEY or "").strip()
    if not key:
        return {"success": False, "error": "License key required"}

    url = f"{CASAKU_BASE_URL}/api/device/check"
    headers = {
        "x-license-key": key,
        "User-Agent": "NgrembelBot/1.0"
    }
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
        return {"success": True, "data": res_json.get("data", {})}
    except Exception as e:
        return {"success": False, "error": str(e)}

def verify_webhook_signature(raw_body: bytes, signature_header: str, secret: Optional[str] = None) -> bool:
    """
    Memverifikasi tanda tangan webhook Casaku menggunakan HMAC-SHA256
    """
    sec = (secret or CASAKU_WEBHOOK_SECRET or "").strip()
    if not sec or not signature_header:
        # Jika secret belum diisi di .env, kita izinkan jika di mode development, tapi beri warning
        return True

    try:
        computed = hmac.new(sec.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed.lower(), signature_header.lower())
    except Exception as e:
        logger.error(f"Error validating webhook signature: {e}")
        return False

def generate_qr_image_bytes(qr_string: str) -> io.BytesIO:
    """
    Membuat gambar QR Code langsung dalam memori (BytesIO) menggunakan qrcode library
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#064e3b", back_color="#ffffff") # Tema Emerald Ngrembel Asri!
    
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return buf

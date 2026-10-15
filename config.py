import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env", override=True)
except Exception:
    pass

# Fallback parser if dotenv not available
env_file = BASE_DIR / ".env"
if env_file.exists():
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and (k not in os.environ or not os.environ[k]):
                        os.environ[k] = v
    except Exception:
        pass

# Telegram Bot Config
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Casaku Payment Gateway Config
CASAKU_LICENSE_KEY = os.getenv("CASAKU_LICENSE_KEY", "").strip()
CASAKU_QR_ID = os.getenv("CASAKU_QR_ID", "").strip()
CASAKU_WEBHOOK_SECRET = os.getenv("CASAKU_WEBHOOK_SECRET", "").strip()
CASAKU_PACKAGE_ID = os.getenv("CASAKU_PACKAGE_ID", "id.dana").strip()

# Web Admin Config
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123").strip()
SECRET_KEY = os.getenv("SECRET_KEY", "ngrembel_asri_secret_super_key_2026").strip()
SESSION_COOKIE_NAME = "ngrembel_session"

# Server Config
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0").strip()
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))

# Database
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "ngrembel.db"))

# Directories
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOAD_DIR = STATIC_DIR / "uploads"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

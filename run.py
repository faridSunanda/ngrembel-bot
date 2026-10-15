import asyncio
import logging
import sys
import uvicorn
import database
from config import BOT_TOKEN, WEB_HOST, WEB_PORT
import bot
from web_app import app as fastapi_app

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ngrembel_runner")

async def main():
    logger.info("==================================================")
    logger.info("   MEMULAI SISTEM BOT & ADMIN WISATA NGREMBEL ASRI  ")
    logger.info("==================================================")

    # 1. Inisialisasi Database SQLite
    logger.info("Memeriksa & menginisialisasi database SQLite...")
    database.init_db()
    logger.info("Database SQLite siap digunakan!")

    # 2. Inisialisasi Bot Telegram (jika token ada)
    telegram_app = None
    if BOT_TOKEN and BOT_TOKEN.strip() and BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.info("Inisialisasi Telegram Bot...")
        try:
            telegram_app = bot.build_application()
            if telegram_app:
                await telegram_app.initialize()
                await telegram_app.start()
                await telegram_app.updater.start_polling(drop_pending_updates=True)
                bot_info = await telegram_app.bot.get_me()
                logger.info(f"Bot Telegram AKTIF sebagai @{bot_info.username} ({bot_info.first_name})")
        except Exception as e:
            logger.error(f"Gagal menjalankan Bot Telegram: {e}")
            logger.warning("Web Admin tetap berjalan. Pastikan BOT_TOKEN di file .env valid.")
    else:
        logger.warning("PERINGATAN: BOT_TOKEN belum diisi atau masih default di file .env!")
        logger.warning("Silakan masukkan token bot Telegram Anda di file .env agar bot dapat berjalan.")
        logger.warning("Web Admin tetap dapat dibuka di http://localhost:8000")

    # 3. Jalankan Web Server Uvicorn (FastAPI)
    server_config = uvicorn.Config(
        app=fastapi_app,
        host=WEB_HOST,
        port=WEB_PORT,
        log_level="info",
        loop="asyncio"
    )
    server = uvicorn.Server(server_config)

    logger.info(f"Admin Web Dashboard berjalan di: http://localhost:{WEB_PORT}")
    logger.info(f"Login Admin Default: Username='admin', Password='admin123'")

    try:
        await server.serve()
    finally:
        if telegram_app:
            logger.info("Menghentikan Telegram Bot...")
            await telegram_app.updater.stop()
            await telegram_app.stop()
            await telegram_app.shutdown()
        logger.info("Sistem telah dimatikan dengan aman.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Program dihentikan oleh pengguna.")

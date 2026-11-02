import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

import config
from database import init_db
from middlewares.auth import AuthMiddleware
from middlewares.rate_limit import RateLimitMiddleware

from handlers import (
    common,
    curriculum,
    books,
    search,
    group_links,
    upload,
    admin
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("tarbiwi_bot")

async def health_check_handler(request):
    return web.Response(text="Tarbiwi Bot is running healthy 24/7!", content_type="text/plain")

async def start_health_server():
    port = int(os.getenv("PORT", "8080"))
    app = web.Application()
    app.router.add_get("/", health_check_handler)
    app.router.add_get("/health", health_check_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check web server running on port {port}")
    return runner

async def main():
    logger.info("Initializing Tarbiwi Bot...")

    # Initialize Database and seed data safely
    await init_db()
    logger.info("Database initialized successfully.")

    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set in .env! Please set your Telegram bot token.")
        print("\n[!] خطأ: لم يتم ضبط BOT_TOKEN داخل ملف .env. يرجى إدخال التوكن لبدء تشغيل البوت.\n")
        return

    # Start health check server if PORT is provided (e.g. Render, Railway, cloud hosts)
    web_runner = None
    if os.getenv("PORT"):
        web_runner = await start_health_server()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register Middlewares
    dp.update.outer_middleware(AuthMiddleware())
    dp.message.middleware(RateLimitMiddleware())

    # Include Handlers
    dp.include_router(common.router)
    dp.include_router(curriculum.router)
    dp.include_router(books.router)
    dp.include_router(search.router)
    dp.include_router(group_links.router)
    dp.include_router(upload.router)
    dp.include_router(admin.router)

    # Register bot commands for groups (shown in the / menu) and private chats
    try:
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="🤖 بدء المحادثة مع البوت في الخاص"),
            ],
            scope=BotCommandScopeAllGroupChats()
        )
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="🏠 القائمة الرئيسية"),
                BotCommand(command="help", description="❓ دليل الاستخدام والمساعدة"),
            ],
            scope=BotCommandScopeAllPrivateChats()
        )
        logger.info("Bot commands registered successfully for groups and private chats.")
    except Exception as e:
        logger.warning(f"Could not register bot commands: {e}")

    logger.info("Starting bot polling...")
    try:
        # Drop pending updates to avoid processing backlog
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        if web_runner:
            await web_runner.cleanup()
        logger.info("Bot stopped cleanly.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Process terminated by user.")

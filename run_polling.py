
import asyncio
from bot import make_bot, router
from db import init_db
from aiogram import F

async def main():
    await init_db()
    bot, dp = make_bot()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

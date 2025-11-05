import os
import json
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from texts import HELP_TEXT, HEADER, TEMPLATE_ROW, ERROR_NOT_NUMBER
from logic import full_table
from db import SessionLocal, upsert_user, CalcLog
from sqlalchemy.ext.asyncio import AsyncSession

# Админы из переменной окружения, пример: "123456789,987654321"
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
BOT_TOKEN = os.getenv("BOT_TOKEN")

router = Router()

# /start
@router.message(CommandStart())
async def start(m: Message):
    await m.answer(HELP_TEXT)

# /help
@router.message(Command("help"))
async def help_cmd(m: Message):
    extra = (
        "\n\nℹ️ Вся подробная информация о том, как работают бусты — "
        "в нашем канале:\n👉 https://t.me/kak_rabotaut_boost_v_telegram/3"
    )
    await m.answer(HELP_TEXT + extra)

# /broadcast (только для админов): /broadcast <текст>
@router.message(Command("broadcast"))
async def broadcast_cmd(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return await m.answer("⛔ У вас нет прав для рассылки.")
    # текст сразу после команды
    text = m.text.split(maxsplit=1)
    if len(text) < 2 or not text[1].strip():
        return await m.answer("Использование: <code>/broadcast Текст сообщения</code>")
    payload = text[1].strip()

    sent = 0
    async with SessionLocal() as session:
        users = await session.execute(
            CalcLog.__table__.select().with_only_columns(CalcLog.user_id).distinct()
        )
        # Получаем Telegram ID пользователей
        user_ids = set()
        for row in users:
            # row.user_id -> надо получить tg_id из таблицы пользователей
            pass  # простой вариант оставим рассылку в админке webapp.py

    # В боте оставим ответ и перенаправим в админку
    return await m.answer("Для рассылки используйте веб-админку: /admin → форма рассылки.")

# Основной калькулятор: сообщение — число подписчиков
@router.message(F.text.regexp(r"^\s*\d+\s*$"))
async def calc(m: Message):
    subs = int(m.text.strip())
    table = full_table(subs)

    lines = [HEADER.format(subs=subs)]
    # уровни 1..10
    for lvl in range(1, 11):
        lines.append(TEMPLATE_ROW.format(level=lvl, value=table[lvl]))
    # добавляем 50-й уровень
    fifty = full_table(subs, [50])[50]
    lines.append(TEMPLATE_ROW.format(level=50, value=fifty))

    text = "\n".join(lines)
    await m.answer(text)

    # Сообщение о покупке бустов
    await m.answer("💥 Купить в нашем оф. боте:\n👉 @boostceo_bot")

    # Логируем расчёт в БД
    async with SessionLocal() as session:  # type: AsyncSession
        user = await upsert_user(session, m.from_user.id, m.from_user.first_name, m.from_user.username)
        session.add(CalcLog(user_id=user.id, subscribers=subs, result_json=json.dumps(table)))
        await session.commit()

# Фолбэк
@router.message()
async def fallback(m: Message):
    await m.answer(ERROR_NOT_NUMBER)

def make_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    return bot, dp

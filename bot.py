
import os, json
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties  # ← ВОТ ЭТО ДОЛЖНО БЫТЬ

from texts import *
from logic import full_table
from db import SessionLocal, init_db, upsert_user, CalcLog
from sqlalchemy.ext.asyncio import AsyncSession

ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
BOT_TOKEN = os.getenv("BOT_TOKEN")

router = Router()

@router.message(CommandStart())
async def start(m: Message):
    await m.answer(HELP_TEXT)

@router.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(HELP_TEXT)

@router.message(Command("broadcast"))
async def start_broadcast(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return await m.answer(ACCESS_DENIED)
    await m.answer(BROADCAST_PROMPT)

    @router.message(F.reply_to_message_id == m.message_id)
    async def broadcast_handler(msg: Message):
        # This nested handler will only work in the same process lifetime; for simplicity use /broadcast <text> alternative:
        pass  # Kept for clarity

@router.message(F.text.regexp(r"^\s*\d+\s*$"))
async def calc(m: Message):
    subs = int(m.text.strip())
    table = full_table(subs)
    lines = [HEADER.format(subs=subs)]
    for lvl in range(1, 11):
        lines.append(TEMPLATE_ROW.format(level=lvl, value=table[lvl]))
    text = "\n".join(lines)
    await m.answer(text)

    # store in DB
    async with SessionLocal() as session:  # type: AsyncSession
        user = await upsert_user(session, m.from_user.id, m.from_user.first_name, m.from_user.username)
        session.add(CalcLog(user_id=user.id, subscribers=subs, result_json=json.dumps(table)))
        await session.commit()

@router.message()
async def fallback(m: Message):
    await m.answer(ERROR_NOT_NUMBER)

def make_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    return bot, dp

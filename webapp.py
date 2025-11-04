
import os, json, asyncio
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from aiogram.types import Update
from aiogram import Bot
from itsdangerous import Signer
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db import SessionLocal, init_db, User, CalcLog
from bot import make_bot, router, ADMIN_IDS
from logic import full_table

security = HTTPBasic()
templates = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "/webhook/secret-path")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

app = FastAPI(title="Boosts Counter Bot")

bot, dp = make_bot()

@app.on_event("startup")
async def on_startup():
    await init_db()
    if BASE_URL:
        await bot.set_webhook(f"{BASE_URL}{WEBHOOK_SECRET_PATH}")
    else:
        print("BASE_URL не задан — вебхук не выставлен (используйте polling или задайте BASE_URL).")

@app.post(WEBHOOK_SECRET_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}

def check_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = credentials.username == "admin"
    correct_password = credentials.password == ADMIN_PASSWORD
    if not (correct_username and correct_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})
    return True

@app.get("/", response_class=HTMLResponse)
async def index():
    tpl = templates.get_template("index.html")
    return tpl.render()

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(auth: bool = Depends(check_admin)):
    async with SessionLocal() as session:
        # totals
        total_users = (await session.execute(select(func.count()).select_from(User))).scalar_one()
        total_calcs = (await session.execute(select(func.count()).select_from(CalcLog))).scalar_one()

        # daily activity last 30 days
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(days=30)
        rows = (await session.execute(
            select(func.date(CalcLog.created_at), func.count())
            .where(CalcLog.created_at >= since)
            .group_by(func.date(CalcLog.created_at))
            .order_by(func.date(CalcLog.created_at))
        )).all()
        labels = [str(r[0]) for r in rows]
        values = [r[1] for r in rows]

        # top users
        top = (await session.execute(
            select(User.username, func.count(CalcLog.id))
            .join(CalcLog, CalcLog.user_id == User.id)
            .group_by(User.id)
            .order_by(func.count(CalcLog.id).desc())
            .limit(10)
        )).all()

    tpl = templates.get_template("admin.html")
    return tpl.render(total_users=total_users, total_calcs=total_calcs,
                      labels=labels, values=values, top=top)

@app.post("/admin/broadcast", response_class=HTMLResponse)
async def admin_broadcast(text: str = Form(...), auth: bool = Depends(check_admin)):
    async with SessionLocal() as session:
        users = (await session.execute(select(User.tg_id))).scalars().all()
    ok = 0
    for uid in users:
        try:
            await bot.send_message(uid, text)
            ok += 1
        except Exception:
            pass
    tpl = templates.get_template("broadcast_done.html")
    return tpl.render(ok=ok, total=len(users))

# --- Добавляем после всех остальных маршрутов ---
from fastapi.responses import PlainTextResponse

@app.get("/ping", response_class=PlainTextResponse)
async def ping():
    return "pong"

@app.get("/healthz", response_class=PlainTextResponse)
async def healthz():
    return "ok"
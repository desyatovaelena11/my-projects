import json
import logging
import httpx
from fastapi import APIRouter, Request
from sqlalchemy import select, update

from database import SessionLocal
from models import Master

router = APIRouter()
logger = logging.getLogger("webhook")

TMA_BASE_URL = "https://desyatovaelena11.github.io/my-projects/olga-project/tg-app/"


async def tg_send(token: str, method: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, timeout=10)
    result = r.json()
    if not result.get("ok"):
        logger.error(f"tg_send {method} failed: {result}")
    return result


@router.post("/webhook/telegram/{bot_token}")
async def telegram_webhook(bot_token: str, request: Request):
    body = await request.json()
    logger.info(f"Webhook body keys: {list(body.keys())}")

    async with SessionLocal() as db:
        result = await db.execute(
            select(Master).where(
                Master.bot_token == bot_token,
                Master.is_active == True,
            )
        )
        master = result.scalar_one_or_none()

    if not master:
        logger.warning(f"Master not found for token: {bot_token[:20]}...")
        return {"ok": True}

    message = body.get("message") or body.get("edited_message")
    if not message:
        logger.info(f"No message in body, update type: {list(body.keys())}")
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    logger.info(f"Message from chat_id={chat_id}, text={text[:50] if text else ''}")

    web_app_data = message.get("web_app_data")
    if web_app_data:
        logger.info(f"Got web_app_data: {web_app_data}")
        await _handle_booking(bot_token, master, chat_id, message, web_app_data["data"])
        return {"ok": True}

    if text.startswith("/start"):
        await _handle_start(bot_token, master, chat_id)
        return {"ok": True}

    return {"ok": True}


async def _handle_start(bot_token: str, master, chat_id: int):
    # Если мастер ещё не зарегистрировал свой Telegram ID — сохраняем автоматически
    if not master.telegram_id or master.telegram_id == 123456789:
        async with SessionLocal() as db:
            await db.execute(
                update(Master)
                .where(Master.id == master.id)
                .values(telegram_id=chat_id)
            )
            await db.commit()
        logger.info(f"Auto-saved telegram_id={chat_id} for master slug={master.slug}")

    tma_url = f"{TMA_BASE_URL}?startapp={master.slug}"
    result = await tg_send(bot_token, "sendMessage", {
        "chat_id": chat_id,
        "text": (
            f"Привет! 👋\n\n"
            f"Это страница записи к мастеру *{master.name}*.\n"
            f"Нажми кнопку ниже, чтобы посмотреть услуги и записаться."
        ),
        "parse_mode": "Markdown",
        "reply_markup": {
            "keyboard": [[
                {"text": "💅 Открыть каталог", "web_app": {"url": tma_url}}
            ]],
            "resize_keyboard": True,
            "one_time_keyboard": False,
        },
    })
    logger.info(f"_handle_start result: {result.get('ok')}")


async def _handle_booking(bot_token: str, master, client_chat_id: int, message: dict, data_str: str):
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse booking data: {data_str}")
        return

    client_name = message.get("from", {}).get("first_name", "Клиент")
    client_username = message.get("from", {}).get("username", "")
    client_mention = f"@{client_username}" if client_username else client_name

    service_name = data.get("service_name", "—")
    price = data.get("service_price", "—")
    duration = data.get("service_duration", "—")
    booking_label = data.get("booking_label", "")

    datetime_line = f"📅 Дата и время: {booking_label}\n" if booking_label else ""

    master_text = (
        f"📩 *Новая заявка!*\n\n"
        f"👤 Клиент: {client_mention}\n"
        f"💅 Услуга: {service_name}\n"
        f"{datetime_line}"
        f"💰 Стоимость: {price} ₽\n"
        f"⏱ Длительность: {duration} мин\n\n"
        f"Клиент ждёт подтверждения — напиши ему в Telegram."
    )
    r1 = await tg_send(bot_token, "sendMessage", {
        "chat_id": master.telegram_id,
        "text": master_text,
        "parse_mode": "Markdown",
    })
    logger.info(f"Notify master result: {r1}")

    client_datetime = f" на *{booking_label}*" if booking_label else ""
    r2 = await tg_send(bot_token, "sendMessage", {
        "chat_id": client_chat_id,
        "text": (
            f"✅ Заявка отправлена!\n\n"
            f"Вы записались{client_datetime}.\n"
            f"*{master.name}* получила запрос и напишет в Telegram для подтверждения."
        ),
        "parse_mode": "Markdown",
    })
    logger.info(f"Notify client result: {r2}")

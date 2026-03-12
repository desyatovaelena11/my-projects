"""
Точка входа FastAPI — здесь стартует весь сервер.

Запуск локально:
  cd backend
  uvicorn main:app --reload

После запуска открой в браузере:
  http://localhost:8000          → {"status": "ok"}
  http://localhost:8000/docs     → интерактивная документация API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.public import router as public_router
from api.admin import router as admin_router
from webhooks.telegram import router as webhook_router

app = FastAPI(
    title="Ma Master API",
    description="API платформы для мастеров маникюра",
    version="1.0.0",
)

# CORS — разрешаем TMA (другой домен) обращаться к нашему API.
# allow_origins=["*"] подходит для разработки.
# После деплоя заменить на реальный домен TMA.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Публичные эндпоинты (/api/v1/{slug}/...)
app.include_router(public_router)

# Панель мастера (/admin/...)
app.include_router(admin_router)

# Webhook для Telegram-ботов (/webhook/telegram/{bot_token})
app.include_router(webhook_router)


@app.get("/")
def health_check():
    """Проверка: сервер живой."""
    return {"status": "ok"}

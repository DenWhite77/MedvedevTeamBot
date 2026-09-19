"""
Модуль handlers/admin/__init__.py

Собирает роутеры всех админских модулей в один общий роутер.
Позволяет в main.py делать: from handlers import admin; admin.router
"""
from aiogram import Router

from . import events
from . import settings
from . import participants


router = Router(name="admin")
router.include_router(events.router)
router.include_router(settings.router)
router.include_router(participants.router)

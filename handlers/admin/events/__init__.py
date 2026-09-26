"""
Модуль handlers/admin/events/__init__.py

Собирает все подроутеры для работы с событиями в один роутер.
Экспортирует `router` для использования в handlers/admin/__init__.py.
"""
from aiogram import Router

from .create import router_create
from .publish import router_publish
from .delete import router_delete


router = Router(name="admin_events")
router.include_router(router_create)
router.include_router(router_publish)
router.include_router(router_delete)

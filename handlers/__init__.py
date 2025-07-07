from aiogram import Router

from .profile import router as profile_router
from .admin import router as admin_router
# В keyboards.py обычно только клавиатуры, роутера нет, поэтому импортировать не нужно

router = Router()
router.include_router(profile_router)
router.include_router(admin_router)

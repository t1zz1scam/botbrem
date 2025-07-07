from aiogram import Router

from .profile import router as profile_router
from .admin import router as admin_router

router = Router()
router.include_router(profile_router)
router.include_router(admin_router)

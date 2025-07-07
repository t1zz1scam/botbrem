from .profile import router as profile_router
from .admin import router as admin_router

from aiogram import Router

router = Router()
router.include_router(profile_router)
router.include_router(admin_router)

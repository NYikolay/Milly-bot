from aiogram import Router

from src.handlers.common import router as common_router
from src.handlers.errors import router as errors_router

router = Router(name="root")
router.include_router(common_router)
router.include_router(errors_router)

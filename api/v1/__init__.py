from fastapi import APIRouter
from .auth import auth_router
from .requests import requests_router
from .metrics import metrics_router

router = APIRouter(prefix="/v1")

router.include_router(auth_router)
router.include_router(requests_router)
router.include_router(metrics_router)

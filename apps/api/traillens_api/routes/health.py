from fastapi import APIRouter

from .. import __version__

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "version": __version__}


@router.get("/readyz")
def readyz() -> dict:
    # Sprint 4 末:检查 DB/Redis 连通性
    return {"ready": True, "checks": {"db": "stub", "redis": "stub"}}

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def liveness():
    return {"status": "ok"}


@router.get("/readyz")
async def readiness():
    from app.services.queue import get_redis
    try:
        await get_redis().ping()
        return {"status": "ready"}
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(503, "Redis unavailable")

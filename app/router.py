from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """Health check — digunakan untuk monitoring availability."""
    return {"status": "ok", "service": "vates-core", "version": "0.1.0"}

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    """Root — penanda bahwa server hidup."""
    return {"status": "Vates Core is running"}


@router.get("/health")
async def health():
    """Health check — digunakan untuk monitoring availability."""
    return {"status": "ok", "service": "vates-core", "version": "0.1.0"}

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Health check — returns 200 when the server is running."""
    return {"status": "ok"}

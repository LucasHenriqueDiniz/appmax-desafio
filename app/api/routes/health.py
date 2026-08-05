from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.infrastructure.database.session import engine

router = APIRouter()


@router.get("/health")
def health() -> JSONResponse:
    """Nao e so "estou vivo" — e "estou vivo E enxergo o banco"."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "database": "down"})
    return JSONResponse(status_code=200, content={"status": "ok", "database": "up"})

from fastapi import APIRouter, Response

from app.services import health as service

router = APIRouter(tags=["health"])


@router.get("/health", summary="Приложение живо и видит PostgreSQL; degraded, если упал шард")
def health(response: Response):
    result = service.check()
    if result["status"] == "error":
        response.status_code = 503
    return result

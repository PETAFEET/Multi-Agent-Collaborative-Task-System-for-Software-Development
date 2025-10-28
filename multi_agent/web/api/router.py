from fastapi.routing import APIRouter

from multi_agent.web.api import (
    docs,
    dummy,
    echo,
    monitoring,
    planner,
    rabbit,
    redis,
    users,
)

api_router = APIRouter()
api_router.include_router(monitoring.router)
api_router.include_router(users.router)
api_router.include_router(docs.router)
api_router.include_router(echo.router, prefix="/echo", tags=["echo"])
api_router.include_router(dummy.router, prefix="/dummy", tags=["dummy"])
api_router.include_router(redis.router, prefix="/redis", tags=["redis"])
api_router.include_router(rabbit.router, prefix="/rabbit", tags=["rabbit"])
api_router.include_router(planner.router, prefix="/planner", tags=["planner"])

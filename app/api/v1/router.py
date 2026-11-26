from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.reports.router import router as reports_router
from app.modules.statistics.router import router as statistics_router
from app.modules.users.router import router as users_router
from app.modules.visitors.router import router as visitors_router
from app.modules.visits.router import router as visits_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(visitors_router)
api_router.include_router(visits_router)
api_router.include_router(statistics_router)
api_router.include_router(reports_router)

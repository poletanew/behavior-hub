from fastapi import APIRouter

from app.api.v1 import auth, dashboard, invitations, patients, professionals, sessions, trainings

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(invitations.router)
api_router.include_router(patients.router)
api_router.include_router(professionals.router)
api_router.include_router(sessions.router)
api_router.include_router(trainings.router)
api_router.include_router(dashboard.router)

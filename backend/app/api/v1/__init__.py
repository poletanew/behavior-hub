from fastapi import APIRouter

from app.api.v1 import (
    auth,
    dashboard,
    deleted_data,
    invitations,
    patients,
    professionals,
    reports,
    resources,
    sessions,
    trainings,
    treatment_plans,
)

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(invitations.router)
api_router.include_router(patients.router)
api_router.include_router(professionals.router)
api_router.include_router(sessions.router)
api_router.include_router(trainings.router)
api_router.include_router(dashboard.router)
api_router.include_router(treatment_plans.router)
api_router.include_router(reports.router)
api_router.include_router(resources.router)
api_router.include_router(deleted_data.router)

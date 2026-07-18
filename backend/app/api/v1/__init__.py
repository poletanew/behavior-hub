from fastapi import APIRouter

from app.api.v1 import (
    appointments,
    audit_logs,
    auth,
    billing,
    clinical_alerts,
    dashboard,
    deleted_data,
    invitations,
    notifications,
    patients,
    professionals,
    rbac,
    reports,
    resources,
    session_templates,
    sessions,
    timeline,
    trainings,
    treatment_plans,
)

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(billing.router)
api_router.include_router(appointments.router)
api_router.include_router(clinical_alerts.router)
api_router.include_router(timeline.router)
api_router.include_router(invitations.router)
api_router.include_router(patients.router)
api_router.include_router(professionals.router)
api_router.include_router(sessions.router)
api_router.include_router(session_templates.router)
api_router.include_router(trainings.router)
api_router.include_router(dashboard.router)
api_router.include_router(treatment_plans.router)
api_router.include_router(reports.router)
api_router.include_router(resources.router)
api_router.include_router(deleted_data.router)
api_router.include_router(notifications.router)
api_router.include_router(rbac.router)
api_router.include_router(audit_logs.router)

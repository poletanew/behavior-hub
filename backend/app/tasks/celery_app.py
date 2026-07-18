from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "behavior_hub",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.purge", "app.tasks.reminders"],
)

celery_app.conf.beat_schedule = {
    "purge-expired-deleted-data-daily": {
        "task": "app.tasks.purge.purge_expired_soft_deleted_records",
        "schedule": crontab(hour=3, minute=0),
    },
    "send-appointment-reminders-hourly": {
        "task": "app.tasks.reminders.send_appointment_reminders",
        "schedule": crontab(minute=0),
    },
}
celery_app.conf.timezone = "UTC"

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "trackme",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.import_tasks",
        "app.tasks.nav_tasks",
        "app.tasks.alert_tasks",
        "app.tasks.email_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 min max per task
    worker_max_tasks_per_child=100,
)

# Scheduled tasks
celery_app.conf.beat_schedule = {
    "update-navs-daily": {
        "task": "app.tasks.nav_tasks.update_all_navs",
        "schedule": crontab(hour=23, minute=30),  # 11:30 PM IST daily
    },
    "scan-emails-periodic": {
        "task": "app.tasks.email_tasks.scan_all_emails",
        "schedule": crontab(hour="*/6"),  # Every 6 hours
    },
    "check-alerts": {
        "task": "app.tasks.alert_tasks.evaluate_all_alerts",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes during market hours
    },
    "update-market-prices": {
        "task": "app.tasks.nav_tasks.update_market_prices",
        "schedule": crontab(minute="*/15", hour="9-16", day_of_week="1-5"),  # Every 15 min during market hours
    },
}

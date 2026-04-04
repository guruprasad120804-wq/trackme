"""Background tasks for email scanning."""
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.email_tasks.scan_all_emails")
def scan_all_emails():
    """Scan emails for all users with active email configs."""
    import asyncio
    asyncio.run(_scan_all())


async def _scan_all():
    from sqlalchemy import select
    from app.database import async_session
    from app.models.import_log import EmailConfig

    async with async_session() as db:
        result = await db.execute(
            select(EmailConfig).where(EmailConfig.is_active.is_(True))
        )
        configs = result.scalars().all()

        for config in configs:
            try:
                await _scan_user(str(config.user_id), db)
            except Exception:
                pass  # Individual user failures shouldn't block others


@celery_app.task(name="app.tasks.email_tasks.scan_user_emails")
def scan_user_emails(user_id: str):
    """Scan emails for a specific user."""
    import asyncio
    asyncio.run(_scan_user_task(user_id))


async def _scan_user_task(user_id: str):
    from app.database import async_session
    async with async_session() as db:
        await _scan_user(user_id, db)


async def _scan_user(user_id: str, db):
    """Core email scanning logic for a single user."""
    # TODO: Port email scanning logic from reference project
    # 1. Get EmailConfig for user
    # 2. Decrypt OAuth tokens
    # 3. Connect to Gmail API
    # 4. Search for CAS PDFs from CAMS/KFintech
    # 5. Download unprocessed attachments
    # 6. Parse via CAS parser
    # 7. Record in ProcessedEmail
    pass

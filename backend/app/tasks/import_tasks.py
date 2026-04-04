"""Background tasks for CAS import processing."""
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.import_tasks.process_cas_upload")
def process_cas_upload(user_id: str, import_log_id: str, pdf_content: bytes, password: str):
    """Process an uploaded CAS PDF in the background."""
    import asyncio
    asyncio.run(_process_cas(user_id, import_log_id, pdf_content, password))


async def _process_cas(user_id: str, import_log_id: str, pdf_content: bytes, password: str):
    import uuid
    import tempfile
    import os
    from sqlalchemy import select

    from app.database import async_session
    from app.models.import_log import ImportLog

    async with async_session() as db:
        result = await db.execute(select(ImportLog).where(ImportLog.id == uuid.UUID(import_log_id)))
        import_log = result.scalar_one_or_none()
        if not import_log:
            return

        try:
            # Write PDF to temp file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(pdf_content)
                temp_path = f.name

            try:
                from app.services.cas_parser import parse_and_import_cas
                result = await parse_and_import_cas(
                    user_id=user_id,
                    pdf_path=temp_path,
                    password=password,
                    db=db,
                )
                import_log.status = "completed"
                import_log.schemes_added = result.get("schemes_added", 0)
                import_log.transactions_added = result.get("transactions_added", 0)
                import_log.summary_json = result
            finally:
                os.unlink(temp_path)

        except Exception as e:
            import_log.status = "failed"
            import_log.error_details = str(e)
            import_log.errors = 1

        await db.commit()

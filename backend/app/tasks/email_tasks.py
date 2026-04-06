"""Background tasks for email scanning."""
import asyncio
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.email_tasks.scan_all_emails")
def scan_all_emails():
    """Scan emails for all users with active email configs."""
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
            except Exception as e:
                logger.error(f"Email scan failed for user {config.user_id}: {e}")


@celery_app.task(name="app.tasks.email_tasks.scan_user_emails")
def scan_user_emails(user_id: str):
    """Scan emails for a specific user."""
    asyncio.run(_scan_user_task(user_id))


async def _scan_user_task(user_id: str):
    from app.database import async_session
    async with async_session() as db:
        await _scan_user(user_id, db)


async def _scan_user(user_id: str, db):
    """Core email scanning logic for a single user.

    1. Load EmailConfig and decrypt tokens
    2. Build Gmail API service
    3. Search for CAS emails from CAMS/KFintech/MFCentral
    4. Download unprocessed PDF attachments
    5. Parse via casparser and import
    6. Record in ProcessedEmail + ImportLog
    """
    from sqlalchemy import select
    from app.models.import_log import EmailConfig, ProcessedEmail, ImportLog
    from app.utils.security import decrypt_value, encrypt_value
    from app.services.gmail_service import (
        build_gmail_service,
        search_cas_emails,
        get_message_details,
        download_attachment,
        find_pdf_attachments,
        get_message_subject,
    )
    from app.services.cas_parser import parse_and_import_cas

    uid = uuid.UUID(user_id)

    # 1. Get EmailConfig
    result = await db.execute(
        select(EmailConfig).where(EmailConfig.user_id == uid)
    )
    config = result.scalar_one_or_none()

    if not config or not config.is_active:
        return {"status": "skipped", "reason": "not configured"}
    if not config.oauth_token_encrypted or not config.oauth_refresh_token_encrypted:
        return {"status": "skipped", "reason": "no OAuth tokens"}
    if not config.cas_password_encrypted:
        return {"status": "skipped", "reason": "no CAS password — set it in Settings > Email Scanning"}

    # 2. Decrypt tokens and build Gmail service
    access_token = decrypt_value(config.oauth_token_encrypted)
    refresh_token = decrypt_value(config.oauth_refresh_token_encrypted)
    cas_password = decrypt_value(config.cas_password_encrypted)

    service, creds = await asyncio.to_thread(build_gmail_service, access_token, refresh_token)

    # If token was refreshed, save the new access token
    if creds.token != access_token:
        config.oauth_token_encrypted = encrypt_value(creds.token)

    # 3. Search for CAS emails
    after_date = config.last_scanned if config.last_scanned else None
    messages = await asyncio.to_thread(search_cas_emails, service, after_date)

    stats = {"emails_found": len(messages), "processed": 0, "imported": 0, "errors": []}

    # 4. Process each message
    for msg_stub in messages:
        msg_id = msg_stub["id"]

        # Check if already processed
        existing = await db.execute(
            select(ProcessedEmail).where(
                ProcessedEmail.user_id == uid,
                ProcessedEmail.gmail_message_id == msg_id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        try:
            msg = await asyncio.to_thread(get_message_details, service, msg_id)
            subject = get_message_subject(msg)
            pdf_attachments = find_pdf_attachments(msg)

            for att in pdf_attachments:
                # Download PDF
                pdf_bytes = await asyncio.to_thread(
                    download_attachment, service, msg_id, att["attachment_id"]
                )

                # Write to temp file
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(pdf_bytes)
                    temp_path = f.name

                try:
                    # Parse and import
                    import_result = await parse_and_import_cas(
                        user_id=user_id,
                        pdf_path=temp_path,
                        password=cas_password,
                        db=db,
                    )
                    stats["imported"] += 1

                    # Create import log
                    import_log = ImportLog(
                        user_id=uid,
                        source="email_scan",
                        status="completed",
                        file_name=att["filename"],
                        schemes_added=import_result.get("schemes_added", 0),
                        transactions_added=import_result.get("transactions_added", 0),
                        errors=len(import_result.get("errors", [])),
                        error_details="; ".join(import_result.get("errors", [])) if import_result.get("errors") else None,
                        summary_json=import_result,
                    )
                    db.add(import_log)
                except Exception as parse_err:
                    logger.warning(f"Failed to parse CAS from email {msg_id}: {parse_err}")
                    # Not all PDF attachments from these senders are CAS files — skip gracefully
                finally:
                    os.unlink(temp_path)

            # Record as processed
            pe = ProcessedEmail(
                user_id=uid,
                gmail_message_id=msg_id,
                subject=subject[:500] if subject else "",
                status="success",
            )
            db.add(pe)
            stats["processed"] += 1

        except Exception as e:
            logger.error(f"Failed to process email {msg_id}: {e}")
            pe = ProcessedEmail(
                user_id=uid,
                gmail_message_id=msg_id,
                subject="",
                status="failed",
                error_message=str(e)[:500],
            )
            db.add(pe)
            stats["errors"].append(str(e))

    # 5. Update last_scanned
    config.last_scanned = datetime.now(timezone.utc)
    await db.commit()

    return stats

import tempfile
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.import_log import ImportLog
from app.utils.dependencies import get_current_user

router = APIRouter()


@router.post("/cas-upload")
async def upload_cas(
    file: UploadFile = File(...),
    password: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a CAS PDF for parsing and import."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be under 50MB")

    content = await file.read()

    import_log = ImportLog(
        user_id=user.id,
        source="cas_upload",
        status="processing",
        file_name=file.filename,
    )
    db.add(import_log)
    await db.commit()

    # Process inline (no Celery required)
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            from app.services.cas_parser import parse_and_import_cas
            result = await parse_and_import_cas(
                user_id=str(user.id),
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
    return {
        "import_id": str(import_log.id),
        "status": import_log.status,
        "schemes_added": import_log.schemes_added,
        "transactions_added": import_log.transactions_added,
    }


@router.post("/manual")
async def manual_transaction(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a manual transaction."""
    from app.services.manual_entry import process_manual_transaction
    result = await process_manual_transaction(user_id=str(user.id), data=body, db=db)
    return result


@router.get("/history")
async def get_import_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ImportLog)
        .where(ImportLog.user_id == user.id)
        .order_by(ImportLog.created_at.desc())
        .limit(50)
    )
    logs = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "source": log.source,
            "status": log.status,
            "file_name": log.file_name,
            "schemes_added": log.schemes_added,
            "transactions_added": log.transactions_added,
            "errors": log.errors,
            "created_at": str(log.created_at),
        }
        for log in logs
    ]


@router.post("/email/scan-now")
async def trigger_email_scan(
    user: User = Depends(get_current_user),
):
    """Trigger an immediate email scan for CAS statements."""
    # TODO: Run inline when Celery is not available
    return {"status": "email_scanning_not_available", "message": "Email scanning requires background workers. Coming soon."}

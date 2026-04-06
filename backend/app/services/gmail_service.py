"""Gmail API client for CAS email detection and download."""
import base64
from datetime import datetime

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.config import get_settings

# Known CAS email senders
CAS_SENDERS = [
    "noreply@camsonline.com",
    "donotreply@kfintech.com",
    "noreply@mfcentral.com",
]

CAS_SEARCH_QUERY = (
    "from:({}) has:attachment filename:pdf".format(
        " OR ".join(CAS_SENDERS)
    )
)


def build_gmail_service(
    access_token: str,
    refresh_token: str,
) -> tuple:
    """Build an authenticated Gmail API service.

    Returns (service, credentials) — credentials may have been refreshed.
    """
    settings = get_settings()
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
    # Refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds), creds


def search_cas_emails(
    service,
    after_date: datetime | None = None,
) -> list[dict]:
    """Search Gmail for CAS PDF emails. Returns list of message stubs."""
    query = CAS_SEARCH_QUERY
    if after_date:
        query += f" after:{after_date.strftime('%Y/%m/%d')}"
    results = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=20)
        .execute()
    )
    return results.get("messages", [])


def get_message_details(service, message_id: str) -> dict:
    """Fetch full message with headers and parts."""
    return (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )


def download_attachment(service, message_id: str, attachment_id: str) -> bytes:
    """Download a specific attachment as bytes."""
    att = (
        service.users()
        .messages()
        .attachments()
        .get(userId="me", messageId=message_id, id=attachment_id)
        .execute()
    )
    return base64.urlsafe_b64decode(att["data"])


def find_pdf_attachments(message: dict) -> list[dict]:
    """Extract PDF attachment info from message parts."""
    attachments = []
    parts = message.get("payload", {}).get("parts", [])
    for part in parts:
        filename = part.get("filename", "")
        att_id = part.get("body", {}).get("attachmentId")
        if filename.lower().endswith(".pdf") and att_id:
            attachments.append({
                "filename": filename,
                "attachment_id": att_id,
            })
    return attachments


def get_message_subject(message: dict) -> str:
    """Extract subject header from message."""
    for header in message.get("payload", {}).get("headers", []):
        if header["name"].lower() == "subject":
            return header["value"]
    return ""

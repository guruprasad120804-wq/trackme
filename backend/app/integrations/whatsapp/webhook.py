"""WhatsApp webhook handler for incoming messages."""
import hmac
import hashlib

from fastapi import APIRouter, Request, HTTPException, Query

from app.config import get_settings
from app.integrations.whatsapp.bot import handle_whatsapp_message

settings = get_settings()
router = APIRouter()


@router.get("/webhook/whatsapp")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    """WhatsApp webhook verification (GET request)."""
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/whatsapp")
async def receive_webhook(request: Request):
    """Handle incoming WhatsApp messages."""
    body = await request.json()

    # Verify webhook signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    raw_body = await request.body()
    expected = "sha256=" + hmac.new(
        settings.whatsapp_webhook_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Process messages
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])

            for msg in messages:
                phone = msg.get("from", "")
                msg_type = msg.get("type", "")
                text = ""

                if msg_type == "text":
                    text = msg.get("text", {}).get("body", "")
                elif msg_type == "interactive":
                    text = msg.get("interactive", {}).get("button_reply", {}).get("title", "")

                if text and phone:
                    await handle_whatsapp_message(phone, text)

    return {"status": "ok"}

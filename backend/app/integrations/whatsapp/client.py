"""WhatsApp Business Cloud API client."""
import httpx

from app.config import get_settings

settings = get_settings()

WHATSAPP_API_URL = "https://graph.facebook.com/v19.0"


async def send_whatsapp_message(phone_number: str, message: str) -> dict:
    """Send a text message via WhatsApp Business API."""
    url = f"{WHATSAPP_API_URL}/{settings.whatsapp_phone_number_id}/messages"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.whatsapp_access_token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": message},
            },
        )
        resp.raise_for_status()
        return resp.json()


async def send_whatsapp_template(phone_number: str, template_name: str, parameters: list[str]) -> dict:
    """Send a template message via WhatsApp Business API."""
    url = f"{WHATSAPP_API_URL}/{settings.whatsapp_phone_number_id}/messages"

    components = []
    if parameters:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": p} for p in parameters],
        })

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.whatsapp_access_token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en"},
                    "components": components,
                },
            },
        )
        resp.raise_for_status()
        return resp.json()

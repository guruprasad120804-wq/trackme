from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    metadata: dict | None = None


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    message_count: int


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str
    metadata: dict | None = None

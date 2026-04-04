import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.chat import ChatConversation, ChatMessage
from app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse, MessageResponse
from app.utils.dependencies import get_current_user, require_feature
from app.services.ai_assistant import get_ai_response

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def send_message(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get or create conversation
    if body.conversation_id:
        result = await db.execute(
            select(ChatConversation).where(
                ChatConversation.id == uuid.UUID(body.conversation_id),
                ChatConversation.user_id == user.id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = ChatConversation(user_id=user.id, title=body.message[:50])
        db.add(conversation)
        await db.flush()

    # Save user message
    user_msg = ChatMessage(conversation_id=conversation.id, role="user", content=body.message)
    db.add(user_msg)

    # Get conversation history
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at)
    )
    history = result.scalars().all()

    # Get AI response with portfolio context
    ai_response = await get_ai_response(
        user_id=str(user.id),
        message=body.message,
        history=[(m.role, m.content) for m in history],
        db=db,
    )

    # Save assistant message
    assistant_msg = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=ai_response["content"],
        metadata_json=ai_response.get("metadata"),
    )
    db.add(assistant_msg)
    await db.commit()

    return ChatResponse(
        conversation_id=str(conversation.id),
        message=ai_response["content"],
        metadata=ai_response.get("metadata"),
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatConversation)
        .where(ChatConversation.user_id == user.id)
        .order_by(ChatConversation.updated_at.desc())
    )
    convos = result.scalars().all()

    items = []
    for c in convos:
        count_result = await db.execute(
            select(sqlfunc.count()).where(ChatMessage.conversation_id == c.id)
        )
        count = count_result.scalar() or 0
        items.append(ConversationResponse(
            id=str(c.id),
            title=c.title,
            created_at=str(c.created_at),
            message_count=count,
        ))
    return items


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatConversation).where(
            ChatConversation.id == uuid.UUID(conversation_id),
            ChatConversation.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == uuid.UUID(conversation_id))
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()

    return [
        MessageResponse(
            id=str(m.id),
            role=m.role,
            content=m.content,
            created_at=str(m.created_at),
            metadata=m.metadata_json,
        )
        for m in messages
    ]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatConversation).where(
            ChatConversation.id == uuid.UUID(conversation_id),
            ChatConversation.user_id == user.id,
        )
    )
    convo = result.scalar_one_or_none()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(convo)
    await db.commit()
    return {"status": "deleted"}

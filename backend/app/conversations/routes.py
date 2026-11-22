from typing import List
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.conversations.schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationSummary,
    SendMessageRequest,
    MessageResponse,
)
from app.conversations.service import ConversationService

router = APIRouter(prefix="/conversations", tags=["Conversations & Chat"])


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation thread",
)
async def create_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    return await ConversationService.create_conversation(payload, db)


@router.get(
    "",
    response_model=List[ConversationSummary],
    summary="List all active conversations ordered by recent activity",
)
async def list_conversations(
    db: AsyncSession = Depends(get_db),
):
    return await ConversationService.list_conversations(db)


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get full conversation history and metadata",
)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await ConversationService.get_conversation(conversation_id, db)


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Update conversation title, model, or archive status",
)
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await ConversationService.update_conversation(conversation_id, payload, db)


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation and its message history",
)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    await ConversationService.delete_conversation(conversation_id, db)


@router.post(
    "/{conversation_id}/messages",
    summary="Send user message and receive real-time streaming response (SSE)",
)
async def send_message_and_stream(
    conversation_id: str,
    payload: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    event_generator = ConversationService.stream_chat(
        conversation_id=conversation_id,
        user_content=payload.content,
        db=db,
        override_model=payload.model,
        override_system_prompt=payload.system_prompt,
    )
    return StreamingResponse(
        event_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

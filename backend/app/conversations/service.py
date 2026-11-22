import json
import uuid
from typing import List, Optional, AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message
from app.conversations.schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationSummary,
    MessageResponse,
)
from app.providers.schemas import (
    ProviderType,
    ChatCompletionRequest,
    ChatMessage,
    ChatMessageRole,
)
from app.providers.registry import ProviderRegistry
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import logger


class ConversationService:
    @staticmethod
    async def create_conversation(
        payload: ConversationCreate,
        db: AsyncSession,
    ) -> ConversationResponse:
        # Determine provider and model
        active_provider = await ProviderRegistry.get_active_provider(db)
        p_type = payload.provider_type or active_provider.provider_type.value
        p_model = payload.model or active_provider.default_model or "openai/gpt-4o-mini"
        p_title = payload.title or "New Conversation"

        conv = Conversation(
            id=str(uuid.uuid4()),
            title=p_title,
            provider_type=p_type,
            model=p_model,
            system_prompt=payload.system_prompt,
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

        return ConversationResponse(
            id=conv.id,
            title=conv.title,
            provider_type=conv.provider_type,
            model=conv.model,
            system_prompt=conv.system_prompt,
            is_archived=conv.is_archived,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            messages=[],
        )

    @staticmethod
    async def list_conversations(db: AsyncSession) -> List[ConversationSummary]:
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.is_archived == False)
            .order_by(Conversation.updated_at.desc())
        )
        result = await db.execute(stmt)
        conversations = result.scalars().all()

        summaries: List[ConversationSummary] = []
        for c in conversations:
            count = len(c.messages)
            last_msg = c.messages[-1].content[:100] if count > 0 else None
            summaries.append(
                ConversationSummary(
                    id=c.id,
                    title=c.title,
                    provider_type=c.provider_type,
                    model=c.model,
                    is_archived=c.is_archived,
                    message_count=count,
                    last_message_preview=last_msg,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
            )
        return summaries

    @staticmethod
    async def get_conversation(
        conversation_id: str,
        db: AsyncSession,
    ) -> ConversationResponse:
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()
        if not conv:
            raise ResourceNotFoundException(f"Conversation {conversation_id} not found.")

        messages = [
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                model=m.model,
                provider=m.provider,
                tokens_prompt=m.tokens_prompt,
                tokens_completion=m.tokens_completion,
                created_at=m.created_at,
            )
            for m in conv.messages
        ]

        return ConversationResponse(
            id=conv.id,
            title=conv.title,
            provider_type=conv.provider_type,
            model=conv.model,
            system_prompt=conv.system_prompt,
            is_archived=conv.is_archived,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            messages=messages,
        )

    @staticmethod
    async def update_conversation(
        conversation_id: str,
        payload: ConversationUpdate,
        db: AsyncSession,
    ) -> ConversationResponse:
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()
        if not conv:
            raise ResourceNotFoundException(f"Conversation {conversation_id} not found.")

        if payload.title is not None:
            conv.title = payload.title.strip() or "Untitled Conversation"
        if payload.model is not None:
            conv.model = payload.model
        if payload.system_prompt is not None:
            conv.system_prompt = payload.system_prompt
        if payload.is_archived is not None:
            conv.is_archived = payload.is_archived

        await db.commit()
        await db.refresh(conv)
        return await ConversationService.get_conversation(conv.id, db)

    @staticmethod
    async def delete_conversation(conversation_id: str, db: AsyncSession) -> bool:
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()
        if not conv:
            raise ResourceNotFoundException(f"Conversation {conversation_id} not found.")

        await db.delete(conv)
        await db.commit()
        return True

    @staticmethod
    async def add_message(
        conversation_id: str,
        role: str,
        content: str,
        db: AsyncSession,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> Message:
        msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            model=model,
            provider=provider,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    @staticmethod
    async def stream_chat(
        conversation_id: str,
        user_content: str,
        db: AsyncSession,
        override_model: Optional[str] = None,
        override_system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Processes a chat request in real-time:
        1. Persists user prompt to PostgreSQL.
        2. Gathers conversation context.
        3. Invokes the selected AI provider.
        4. Yields SSE chunks formatted as 'data: {...}\\n\\n'.
        5. Persists the generated assistant response upon completion.
        """
        # Load conversation
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()
        if not conv:
            err_data = json.dumps({"type": "error", "message": f"Conversation {conversation_id} not found."})
            yield f"data: {err_data}\n\n"
            return

        # 1. Save user message
        user_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="user",
            content=user_content,
        )
        db.add(user_msg)

        # Auto-update conversation title from first user prompt if still default
        if conv.title == "New Conversation" and len(conv.messages) == 0:
            clean_title = user_content.strip().split("\n")[0][:40]
            if len(user_content.strip()) > 40:
                clean_title += "..."
            conv.title = clean_title

        await db.commit()

        # 2. Build history
        chat_messages: List[ChatMessage] = []
        for m in conv.messages:
            chat_messages.append(ChatMessage(role=ChatMessageRole(m.role), content=m.content))
        chat_messages.append(ChatMessage(role=ChatMessageRole.USER, content=user_content))

        # 3. Resolve provider and model
        try:
            p_type = ProviderType(conv.provider_type)
        except Exception:
            p_type = ProviderType.OPENROUTER

        model_to_use = override_model or conv.model
        sys_prompt = override_system_prompt or conv.system_prompt

        provider_adapter = await ProviderRegistry.get_adapter_instance(p_type, db=db)

        request = ChatCompletionRequest(
            messages=chat_messages,
            model=model_to_use,
            system_prompt=sys_prompt,
            stream=True,
        )

        full_content: List[str] = []
        chunk_id = None

        # 4. Stream response
        try:
            async for chunk in provider_adapter.chat_stream(request):
                if chunk.error:
                    err_payload = json.dumps({"type": "error", "error": chunk.error})
                    yield f"data: {err_payload}\n\n"
                    return

                if chunk.id:
                    chunk_id = chunk.id

                if chunk.delta:
                    full_content.append(chunk.delta)
                    chunk_payload = json.dumps({"type": "token", "delta": chunk.delta})
                    yield f"data: {chunk_payload}\n\n"

            # 5. Persist assistant message
            assembled_content = "".join(full_content)
            assistant_msg = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role="assistant",
                content=assembled_content,
                model=model_to_use,
                provider=p_type.value,
            )
            db.add(assistant_msg)
            await db.commit()
            await db.refresh(assistant_msg)

            done_payload = json.dumps({
                "type": "done",
                "message_id": assistant_msg.id,
                "content": assembled_content,
                "model": model_to_use,
                "provider": p_type.value,
            })
            yield f"data: {done_payload}\n\n"

        except Exception as exc:
            logger.exception(f"Unhandled error in chat streaming: {exc}")
            err_payload = json.dumps({"type": "error", "error": str(exc)})
            yield f"data: {err_payload}\n\n"

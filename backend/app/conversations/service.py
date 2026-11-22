import re
import json
import time
import uuid
from typing import List, Optional, AsyncIterator, Tuple, Any
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
    ModelMode,
    PricingCategory,
    ChatCompletionRequest,
    ChatMessage,
    ChatMessageRole,
)
from app.providers.registry import ProviderRegistry
from app.providers.model_registry import CentralModelRegistry
from app.providers.model_service import ModelService
from app.conversations.personality import PersonalityService
from app.conversations.context_builder import ContextBuilder
from app.tools.engine import ToolExecutionEngine
from app.tools.schemas import ExecutionStatus
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import logger
from app.core.config import settings


def extract_tool_call(content: str) -> Optional[Tuple[str, dict[str, Any]]]:
    """
    Detects whether LLM output contains an intentional tool call request.
    Extracts tool name and arguments dictionary.
    """
    if not content:
        return None
    # 1. Look for ```json ... ``` blocks
    json_blocks = re.findall(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
    for block in json_blocks:
        try:
            data = json.loads(block)
            if isinstance(data, dict) and data.get("action") == "call_tool" and "tool" in data:
                return str(data["tool"]), data.get("arguments", {})
        except Exception:
            pass

    # 2. Look for raw JSON object with "action": "call_tool"
    matches = re.findall(r'(\{\s*"action"\s*:\s*"call_tool"[\s\S]*?\})', content)
    for match in matches:
        try:
            data = json.loads(match)
            if isinstance(data, dict) and data.get("action") == "call_tool" and "tool" in data:
                return str(data["tool"]), data.get("arguments", {})
        except Exception:
            pass

    return None


DEFAULT_SYSTEM_INSTRUCTION = ContextBuilder.build_system_prompt()



class ConversationService:
    @staticmethod
    async def create_conversation(
        payload: ConversationCreate,
        db: AsyncSession,
    ) -> ConversationResponse:
        active_provider = await ProviderRegistry.get_active_provider(db)
        policy = await ModelService.get_or_create_policy(db)

        p_type = payload.provider_type or active_provider.provider_type.value
        p_model = payload.model or policy.selected_model or active_provider.default_model or "nvidia/nemotron-3.5-lightning:free"

        # Enforce free-only mode on creation
        if policy.model_mode == ModelMode.FREE_ONLY:
            allowed, _ = CentralModelRegistry.validate_model_for_mode(p_model, ModelMode.FREE_ONLY)
            if not allowed:
                p_model = CentralModelRegistry.get_default_model(ModelMode.FREE_ONLY)

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
                metadata_json=m.metadata_json,
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

        policy = await ModelService.get_or_create_policy(db)

        if payload.title is not None:
            conv.title = payload.title.strip() or "Untitled Conversation"
        if payload.model is not None:
            if policy.model_mode == ModelMode.FREE_ONLY:
                allowed, reason = CentralModelRegistry.validate_model_for_mode(payload.model, ModelMode.FREE_ONLY)
                if not allowed:
                    raise ResourceNotFoundException(reason or "Cannot select paid model in Free-Only mode.")
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
        Processes a chat request with multi-model switching, mode enforcement,
        configurable fallback chains, token usage tracking, and cost control.
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
            err_data = json.dumps({"type": "error", "error": f"Conversation {conversation_id} not found."})
            yield f"data: {err_data}\n\n"
            return

        # Load model policy
        policy = await ModelService.get_or_create_policy(db)

        # 1. Enforce operational mode and determine target model
        target_model = override_model or conv.model or policy.selected_model
        if policy.model_mode == ModelMode.FREE_ONLY:
            allowed, reason = CentralModelRegistry.validate_model_for_mode(target_model, ModelMode.FREE_ONLY)
            if not allowed:
                if override_model:
                    # User explicitly asked for a paid model while in free_only mode
                    err_data = json.dumps({
                        "type": "error",
                        "error": reason,
                    })
                    yield f"data: {err_data}\n\n"
                    return
                else:
                    # Fallback silently to guaranteed free default
                    target_model = CentralModelRegistry.get_default_model(ModelMode.FREE_ONLY)
                    conv.model = target_model

        # 2. Build Candidate Chain for Fallback
        candidate_models = [target_model]
        if policy.enable_fallback and policy.model_mode != ModelMode.MANUAL:
            fallbacks = CentralModelRegistry.filter_fallback_chain(
                policy.fallback_models, policy.model_mode
            )
            for fb in fallbacks:
                if fb not in candidate_models:
                    candidate_models.append(fb)

        # 3. Save user message to PostgreSQL
        user_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="user",
            content=user_content,
        )
        db.add(user_msg)

        if conv.title == "New Conversation" and len(conv.messages) == 0:
            clean_title = user_content.strip().split("\n")[0][:40]
            if len(user_content.strip()) > 40:
                clean_title += "..."
            conv.title = clean_title

        await db.commit()

        # 4. Resolve personality settings and memory context
        personality = await PersonalityService.get_personality(db)
        mem_ctx = ""
        try:
            from app.memory.retrieval import retrieve_relevant_memory_context
            mem_ctx = await retrieve_relevant_memory_context(user_content, session=db)
        except Exception as e:
            logger.warning(f"Memory context retrieval failed non-fatally: {e}")

        # 5. Assemble system prompt via centralized ContextBuilder
        tools_catalog = ContextBuilder.format_tools_catalog()
        sys_prompt = ContextBuilder.build_system_prompt(
            personality=personality,
            conversation_system_prompt=conv.system_prompt,
            override_system_prompt=override_system_prompt,
            memory_context=mem_ctx,
            available_tools_description=tools_catalog,
        )


        # 6. Build chat messages with token budgeting & sliding window
        chat_messages: List[ChatMessage] = ContextBuilder.build_chat_messages(
            history=conv.messages,
            current_user_content=user_content,
        )

        # 7. Resolve provider adapter
        try:
            p_type = ProviderType(conv.provider_type)
        except Exception:
            p_type = ProviderType.OPENROUTER

        provider_adapter = await ProviderRegistry.get_adapter_instance(p_type, db=db)

        # Approximate prompt tokens (1 token ~ 4 chars)
        prompt_chars = sum(len(m.content) for m in chat_messages) + len(sys_prompt)
        approx_prompt_tokens = max(1, prompt_chars // 4)

        # 6. Fallback Chain Execution Loop
        streaming_succeeded = False
        last_error = "No available model could fulfill the request."

        for idx, current_model in enumerate(candidate_models):
            is_fallback_attempt = idx > 0
            if is_fallback_attempt:
                notice_payload = json.dumps({
                    "type": "notice",
                    "message": f"Primary model encountered an issue. Automatically falling back to: {current_model}",
                })
                yield f"data: {notice_payload}\n\n"

            request = ChatCompletionRequest(
                messages=chat_messages,
                model=current_model,
                system_prompt=sys_prompt,
                stream=True,
            )

            full_content: List[str] = []
            chunk_id = None
            had_error = False
            start_time = time.perf_counter()

            try:
                stream_iter = provider_adapter.chat_stream(request)
                async for chunk in stream_iter:
                    if chunk.error:
                        had_error = True
                        last_error = chunk.error
                        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                        await ModelService.record_execution_metric(
                            provider_type=p_type.value,
                            model_id=current_model,
                            pricing_category="free" if CentralModelRegistry.is_free_model(current_model) else "paid",
                            prompt_tokens=approx_prompt_tokens,
                            completion_tokens=0,
                            estimated_cost=0.0,
                            latency_ms=latency_ms,
                            status="fallback" if idx + 1 < len(candidate_models) else "error",
                            conversation_id=conversation_id,
                            error_type="stream_chunk_error",
                            error_message=chunk.error,
                            db=db,
                        )
                        break

                    if chunk.id:
                        chunk_id = chunk.id

                    if chunk.delta:
                        full_content.append(chunk.delta)
                        chunk_payload = json.dumps({"type": "token", "delta": chunk.delta})
                        yield f"data: {chunk_payload}\n\n"

                if had_error:
                    # Proceed to next fallback model in the chain
                    continue

                # Stream round 1 finished
                assembled_content = "".join(full_content)
                tool_call = extract_tool_call(assembled_content)

                if tool_call:
                    tool_name, tool_args = tool_call
                    tool_call_notice = json.dumps({"type": "tool_call", "tool": tool_name, "arguments": tool_args})
                    yield f"data: {tool_call_notice}\n\n"

                    # Execute tool via ToolExecutionEngine
                    exec_resp = await ToolExecutionEngine.execute_tool(
                        tool_id=tool_name,
                        arguments=tool_args,
                        conversation_id=conversation_id,
                        db=db,
                    )

                    if exec_resp.status == ExecutionStatus.AWAITING_APPROVAL:
                        approval_notice = json.dumps({
                            "type": "approval_required",
                            "approval_id": exec_resp.approval_id,
                            "tool": tool_name,
                            "reason": exec_resp.error,
                        })
                        yield f"data: {approval_notice}\n\n"

                        approval_text = (
                            f"Action `{tool_name}` requires user approval before execution.\n\n"
                            f"- **Tool**: `{tool_name}`\n"
                            f"- **Reason**: {exec_resp.error or 'Action requires explicit human confirmation.'}\n"
                            f"- **Status**: Awaiting Approval\n\n"
                            f"Please approve or reject this request in the Approvals dashboard."
                        )

                        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                        assistant_msg = Message(
                            id=str(uuid.uuid4()),
                            conversation_id=conversation_id,
                            role="assistant",
                            content=approval_text,
                            model=current_model,
                            provider=p_type.value,
                            tokens_prompt=approx_prompt_tokens,
                            tokens_completion=len(approval_text) // 4,
                            metadata_json=json.dumps({
                                "approval_id": exec_resp.approval_id,
                                "tool_name": tool_name,
                                "status": "awaiting_approval",
                                "latency_ms": latency_ms,
                            }),
                        )
                        db.add(assistant_msg)
                        await db.commit()
                        await db.refresh(assistant_msg)

                        done_payload = json.dumps({
                            "type": "done",
                            "message_id": assistant_msg.id,
                            "content": approval_text,
                            "approval_id": exec_resp.approval_id,
                            "model": current_model,
                            "provider": p_type.value,
                            "latency_ms": latency_ms,
                        })
                        yield f"data: {done_payload}\n\n"
                        streaming_succeeded = True
                        break

                    else:
                        # Tool executed (succeeded or failed)
                        tool_res_notice = json.dumps({
                            "type": "tool_result",
                            "tool": tool_name,
                            "success": exec_resp.success,
                            "result": exec_resp.result,
                            "error": exec_resp.error,
                        })
                        yield f"data: {tool_res_notice}\n\n"
                        yield f"data: {json.dumps({'type': 'reset_buffer'})}\n\n"

                        # Round 2: Feed tool output to model to generate the natural-language response
                        tool_out_data = exec_resp.result if exec_resp.success else {"error": exec_resp.error}
                        round2_msgs = list(chat_messages)
                        round2_msgs.append(ChatMessage(role=ChatMessageRole.ASSISTANT, content=assembled_content))
                        round2_msgs.append(ChatMessage(
                            role=ChatMessageRole.USER,
                            content=f"Tool Execution Result for `{tool_name}`:\n<tool_output tool=\"{tool_name}\">\n{json.dumps(tool_out_data)}\n</tool_output>\nPlease explain the result clearly and directly to the user."
                        ))

                        r2_req = ChatCompletionRequest(
                            messages=round2_msgs,
                            model=current_model,
                            system_prompt=sys_prompt,
                            stream=True,
                        )

                        r2_content: List[str] = []
                        try:
                            r2_stream = provider_adapter.chat_stream(r2_req)
                            async for r2_chunk in r2_stream:
                                if r2_chunk.delta:
                                    r2_content.append(r2_chunk.delta)
                                    yield f"data: {json.dumps({'type': 'token', 'delta': r2_chunk.delta})}\n\n"
                        except Exception as r2_err:
                            logger.warning(f"Round 2 explanation stream failed: {r2_err}")

                        assembled_content = "".join(r2_content) or f"Executed `{tool_name}`: {json.dumps(tool_out_data)}"

                # Stream succeeded!
                streaming_succeeded = True
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                approx_completion_tokens = max(1, len(assembled_content) // 4)
                estimated_cost = CentralModelRegistry.estimate_cost(
                    current_model, approx_prompt_tokens, approx_completion_tokens
                )
                pricing_cat = "free" if CentralModelRegistry.is_free_model(current_model) else "paid"

                # Persist assistant response
                metadata_dict = {
                    "estimated_cost_usd": estimated_cost,
                    "latency_ms": latency_ms,
                    "pricing_category": pricing_cat,
                    "fallback_used": is_fallback_attempt,
                }
                if tool_call:
                    metadata_dict["tool_executed"] = tool_call[0]

                assistant_msg = Message(
                    id=str(uuid.uuid4()),
                    conversation_id=conversation_id,
                    role="assistant",
                    content=assembled_content,
                    model=current_model,
                    provider=p_type.value,
                    tokens_prompt=approx_prompt_tokens,
                    tokens_completion=approx_completion_tokens,
                    metadata_json=json.dumps(metadata_dict),
                )
                db.add(assistant_msg)
                await db.commit()
                await db.refresh(assistant_msg)

                # Record execution metric
                await ModelService.record_execution_metric(
                    provider_type=p_type.value,
                    model_id=current_model,
                    pricing_category=pricing_cat,
                    prompt_tokens=approx_prompt_tokens,
                    completion_tokens=approx_completion_tokens,
                    estimated_cost=estimated_cost,
                    latency_ms=latency_ms,
                    status="success",
                    conversation_id=conversation_id,
                    db=db,
                )

                # Emit completion event with cost & usage telemetry
                done_payload = json.dumps({
                    "type": "done",
                    "message_id": assistant_msg.id,
                    "content": assembled_content,
                    "model": current_model,
                    "provider": p_type.value,
                    "prompt_tokens": approx_prompt_tokens,
                    "completion_tokens": approx_completion_tokens,
                    "estimated_cost_usd": estimated_cost,
                    "pricing_category": pricing_cat,
                    "latency_ms": latency_ms,
                    "fallback_used": is_fallback_attempt,
                })
                yield f"data: {done_payload}\n\n"

                # 7. Asynchronously schedule background memory extraction (Phase 2)
                if settings.MEMORY_EXTRACTION_ENABLED:
                    try:
                        _schedule_background_memory_extraction(
                            user_content=user_content,
                            assistant_content=assembled_content,
                            conversation_id=conversation_id,
                            message_id=assistant_msg.id,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to schedule memory extraction: {e}")

                break

            except Exception as exc:
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                last_error = str(exc)
                logger.warning(f"Error streaming with model {current_model}: {exc}")
                await ModelService.record_execution_metric(
                    provider_type=p_type.value,
                    model_id=current_model,
                    pricing_category="free" if CentralModelRegistry.is_free_model(current_model) else "paid",
                    prompt_tokens=approx_prompt_tokens,
                    completion_tokens=0,
                    estimated_cost=0.0,
                    latency_ms=latency_ms,
                    status="fallback" if idx + 1 < len(candidate_models) else "error",
                    conversation_id=conversation_id,
                    error_type="exception",
                    error_message=str(exc),
                    db=db,
                )
                if idx + 1 < len(candidate_models):
                    continue
                break

        if not streaming_succeeded:
            err_payload = json.dumps({"type": "error", "error": last_error})
            yield f"data: {err_payload}\n\n"


async def _execute_async_memory_extraction(
    user_content: str,
    assistant_content: str,
    conversation_id: str,
    message_id: str,
) -> None:
    """Asynchronously creates a persistent background task record and executes extraction."""
    try:
        from app.database.session import async_session_factory
        from app.tasks.service import TaskService
        async with async_session_factory() as session:
            await TaskService.create_and_dispatch_task(
                session=session,
                task_name="Extract Conversation Memories",
                task_type="memory_extraction",
                input_params={
                    "user_content": user_content,
                    "assistant_content": assistant_content,
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                },
            )
    except Exception as exc:
        logger.warning(f"Background memory extraction encountered non-fatal error: {exc}")


def _schedule_background_memory_extraction(
    user_content: str,
    assistant_content: str,
    conversation_id: str,
    message_id: str,
) -> None:
    """Dispatches asynchronous memory extraction without blocking SSE streaming."""
    import asyncio
    asyncio.create_task(
        _execute_async_memory_extraction(
            user_content=user_content,
            assistant_content=assistant_content,
            conversation_id=conversation_id,
            message_id=message_id,
        )
    )

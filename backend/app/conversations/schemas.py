from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    model: Optional[str] = None
    provider: Optional[str] = None
    tokens_prompt: Optional[int] = None
    tokens_completion: Optional[int] = None
    metadata_json: Optional[str] = None
    created_at: datetime


class ConversationBase(BaseModel):
    title: str = Field(default="New Conversation", max_length=255)
    provider_type: str = "openrouter"
    model: str = "meta-llama/llama-3.3-70b-instruct:free"
    system_prompt: Optional[str] = None


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    provider_type: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    is_archived: Optional[bool] = None


class ConversationResponse(ConversationBase):
    id: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []


class ConversationSummary(BaseModel):
    id: str
    title: str
    provider_type: str
    model: str
    is_archived: bool
    message_count: int
    last_message_preview: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)
    model: Optional[str] = None
    system_prompt: Optional[str] = None

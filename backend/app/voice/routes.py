from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.voice.schemas import (
    TranscriptionResponse,
    CleanTextRequest,
    CleanTextResponse,
    VoicePreferencePayload,
)
from app.voice.service import VoiceService

router = APIRouter(prefix="/voice", tags=["Voice Input & Text-to-Speech"])


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe uploaded speech audio file to text",
)
async def transcribe_audio_endpoint(
    audio: UploadFile = File(..., description="Audio recording file (webm, wav, mp3, ogg, m4a)"),
    db: AsyncSession = Depends(get_db),
):
    content = await audio.read()
    return await VoiceService.transcribe_audio(
        file_bytes=content,
        filename=audio.filename or "recording.webm",
        content_type=audio.content_type or "audio/webm",
        db=db,
    )


@router.post(
    "/clean-for-speech",
    response_model=CleanTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Convert Markdown, tables, and code into clean spoken text for TTS",
)
async def clean_for_speech_endpoint(
    payload: CleanTextRequest,
):
    clean = VoiceService.clean_markdown_for_speech(payload.text)
    word_count = len(clean.split())
    return CleanTextResponse(clean_text=clean, word_count=word_count)


@router.get(
    "/preferences",
    response_model=VoicePreferencePayload,
    summary="Retrieve user voice preferences",
)
async def get_voice_preferences_endpoint(
    db: AsyncSession = Depends(get_db),
):
    return await VoiceService.get_preferences(db)


@router.put(
    "/preferences",
    response_model=VoicePreferencePayload,
    summary="Update and persist user voice preferences",
)
async def update_voice_preferences_endpoint(
    payload: VoicePreferencePayload,
    db: AsyncSession = Depends(get_db),
):
    return await VoiceService.update_preferences(payload, db)

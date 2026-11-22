from typing import Optional, List
from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    text: str = Field(..., description="Transcribed text from speech.")
    language: Optional[str] = Field("en", description="Detected or specified audio language.")
    duration_seconds: Optional[float] = Field(None, description="Audio duration in seconds if known.")
    confidence: Optional[float] = Field(0.95, description="Confidence score of transcription.")


class CleanTextRequest(BaseModel):
    text: str = Field(..., description="Markdown or rich text to convert into speech-ready plain text.")


class CleanTextResponse(BaseModel):
    clean_text: str = Field(..., description="Cleaned, human-friendly text for text-to-speech synthesis.")
    word_count: int = Field(..., description="Estimated word count.")


class SynthesisRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize into speech.")
    voice: Optional[str] = Field(None, description="Voice identifier.")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech rate multiplier (0.5 to 2.0).")
    language: str = Field(default="en", description="Target language code.")


class VoicePreferencePayload(BaseModel):
    enabled: bool = Field(default=True, description="Whether voice input and output features are enabled.")
    auto_play: bool = Field(default=False, description="Whether to automatically play speech for new assistant responses.")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech rate multiplier (0.5x to 2.0x).")
    voice: Optional[str] = Field(None, description="Preferred voice name or ID.")
    language: str = Field(default="en-US", description="Preferred language code.")


class VoiceOption(BaseModel):
    id: str
    name: str
    language: str
    provider: str

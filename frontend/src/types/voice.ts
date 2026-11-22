export interface VoicePreferences {
  enabled: boolean;
  auto_play: boolean;
  speed: number;
  voice: string | null;
  language: string;
}

export interface TranscriptionResponse {
  text: string;
  language?: string;
  duration_seconds?: number;
  confidence?: number;
}

export interface CleanTextResponse {
  clean_text: string;
  word_count: number;
}

import { apiClient } from './api';
import type { VoicePreferences, TranscriptionResponse, CleanTextResponse } from '../types/voice';

class VoiceService {
  private currentUtterance: SpeechSynthesisUtterance | null = null;
  private isSpeaking = false;
  private activeMessageId: string | null = null;
  private onStateChangeCallback: ((isPlaying: boolean, messageId: string | null) => void) | null = null;

  // 1. API: Transcribe audio file to text
  async transcribeAudio(audioBlob: Blob, filename = 'recording.webm'): Promise<TranscriptionResponse> {
    const formData = new FormData();
    formData.append('audio', audioBlob, filename);

    const response = await fetch('/api/v1/voice/transcribe', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData?.error?.message || errData?.detail || 'Audio transcription failed.');
    }

    return await response.json();
  }

  // 2. API: Clean Markdown text into natural spoken speech
  async cleanTextForSpeech(text: string): Promise<string> {
    try {
      const res = await apiClient<CleanTextResponse>('/voice/clean-for-speech', {
        method: 'POST',
        body: JSON.stringify({ text }),
      });
      return res.clean_text;
    } catch {
      // Client-side fallback cleaner if API is unreachable
      return this.clientCleanText(text);
    }
  }

  // 3. API: Voice Preferences
  async getPreferences(): Promise<VoicePreferences> {
    try {
      return await apiClient<VoicePreferences>('/voice/preferences');
    } catch {
      const saved = localStorage.getItem('voice_preferences');
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch {
          // ignore
        }
      }
      return {
        enabled: true,
        auto_play: false,
        speed: 1.0,
        voice: null,
        language: 'en-US',
      };
    }
  }

  async updatePreferences(prefs: VoicePreferences): Promise<VoicePreferences> {
    localStorage.setItem('voice_preferences', JSON.stringify(prefs));
    try {
      return await apiClient<VoicePreferences>('/voice/preferences', {
        method: 'PUT',
        body: JSON.stringify(prefs),
      });
    } catch {
      return prefs;
    }
  }

  // 4. Client-side Text-to-Speech (Web Speech API)
  getAvailableVoices(): SpeechSynthesisVoice[] {
    if (typeof window === 'undefined' || !window.speechSynthesis) return [];
    return window.speechSynthesis.getVoices();
  }

  setOnStateChange(cb: (isPlaying: boolean, messageId: string | null) => void) {
    this.onStateChangeCallback = cb;
  }

  async speak(
    messageId: string,
    rawText: string,
    prefs?: VoicePreferences,
    onFinish?: () => void
  ) {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      alert('Your browser does not support speech synthesis.');
      return;
    }

    // If currently speaking this message, stop it
    if (this.isSpeaking && this.activeMessageId === messageId) {
      this.stop();
      return;
    }

    // Stop any existing utterance
    this.stop();

    // Clean Markdown tables and code for speech
    const cleanText = await this.cleanTextForSpeech(rawText);
    if (!cleanText.trim()) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    const speed = prefs?.speed || 1.0;
    utterance.rate = Math.max(0.5, Math.min(2.0, speed));
    utterance.lang = prefs?.language || 'en-US';

    const voices = this.getAvailableVoices();
    if (prefs?.voice) {
      const selectedVoice = voices.find((v) => v.name === prefs.voice || v.voiceURI === prefs.voice);
      if (selectedVoice) utterance.voice = selectedVoice;
    } else {
      const defaultVoice = voices.find((v) => v.lang.startsWith('en') && v.default) || voices.find((v) => v.lang.startsWith('en'));
      if (defaultVoice) utterance.voice = defaultVoice;
    }

    utterance.onstart = () => {
      this.isSpeaking = true;
      this.activeMessageId = messageId;
      this.onStateChangeCallback?.(true, messageId);
    };

    utterance.onend = () => {
      this.isSpeaking = false;
      this.activeMessageId = null;
      this.currentUtterance = null;
      this.onStateChangeCallback?.(false, null);
      onFinish?.();
    };

    utterance.onerror = (e) => {
      console.warn('Speech synthesis error:', e);
      this.isSpeaking = false;
      this.activeMessageId = null;
      this.currentUtterance = null;
      this.onStateChangeCallback?.(false, null);
      onFinish?.();
    };

    this.currentUtterance = utterance;
    window.speechSynthesis.speak(this.currentUtterance);
  }

  stop() {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    this.isSpeaking = false;
    this.activeMessageId = null;
    this.currentUtterance = null;
    this.onStateChangeCallback?.(false, null);
  }

  getActiveMessageId(): string | null {
    return this.activeMessageId;
  }

  getIsSpeaking(): boolean {
    return this.isSpeaking;
  }

  // Client-side quick Markdown cleaner fallback
  private clientCleanText(text: string): string {
    return text
      .replace(/```[\s\S]*?```/g, ' Code block omitted. ')
      .replace(/\|[^\n]+\|/g, ' ')
      .replace(/[-*#>`_~]/g, ' ')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/https?:\/\/\S+/g, 'link')
      .replace(/\s+/g, ' ')
      .trim();
  }
}

export const voiceService = new VoiceService();

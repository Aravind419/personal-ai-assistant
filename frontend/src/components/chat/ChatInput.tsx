import React, { useState, useRef, useEffect } from 'react';
import { Send, Square, Mic, X, Check, Loader2, AlertCircle } from 'lucide-react';
import { voiceService } from '../../services/voiceService';

interface ChatInputProps {
  onSendMessage: (content: string) => void;
  isStreaming: boolean;
  onStopGeneration?: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isStreaming,
  onStopGeneration,
  disabled = false,
  placeholder = 'Ask anything (Shift+Enter for new line)...',
}) => {
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<any>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  // Clean up recording timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming || disabled) return;
    onSendMessage(trimmed);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  // Start Voice Recording
  const handleStartRecording = async () => {
    setMicError(null);
    if (typeof window === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setMicError('Your browser does not support microphone recording.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];

      // Determine supported mime type
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : MediaRecorder.isTypeSupported('audio/mp4')
        ? 'audio/mp4'
        : '';

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        // Stop all audio tracks to release microphone hardware
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorderRef.current = recorder;
      recorder.start(250); // collect chunks every 250ms
      setIsRecording(true);
      setRecordSeconds(0);

      timerRef.current = setInterval(() => {
        setRecordSeconds((s) => s + 1);
      }, 1000);
    } catch (err: any) {
      console.warn('Microphone error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setMicError('Microphone permission was denied. Please allow microphone access in browser settings.');
      } else {
        setMicError(err?.message || 'Failed to access microphone.');
      }
    }
  };

  // Stop Recording and Transcribe Audio
  const handleStopRecordingAndTranscribe = async () => {
    if (timerRef.current) clearInterval(timerRef.current);
    const recorder = mediaRecorderRef.current;

    if (!recorder || recorder.state !== 'recording') {
      setIsRecording(false);
      return;
    }

    setIsRecording(false);
    setIsTranscribing(true);

    recorder.onstop = async () => {
      // Release tracks
      recorder.stream.getTracks().forEach((track) => track.stop());

      const mimeType = recorder.mimeType || 'audio/webm';
      const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
      audioChunksRef.current = [];

      if (audioBlob.size === 0) {
        setIsTranscribing(false);
        setMicError('No audio data was recorded. Please speak clearly into your microphone.');
        return;
      }

      try {
        const filename = mimeType.includes('mp4') ? 'recording.m4a' : 'recording.webm';
        const res = await voiceService.transcribeAudio(audioBlob, filename);
        if (res.text) {
          setInput((prev) => (prev ? `${prev} ${res.text}` : res.text));
        }
      } catch (err: any) {
        setMicError(err?.message || 'Audio transcription failed. You can also type your message.');
      } finally {
        setIsTranscribing(false);
      }
    };

    recorder.stop();
  };

  // Cancel Recording without transcribing
  const handleCancelRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stream.getTracks().forEach((t) => t.stop());
      mediaRecorderRef.current.stop();
    }
    audioChunksRef.current = [];
    setIsRecording(false);
    setRecordSeconds(0);
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="p-4 bg-slate-950/90 border-t border-slate-800 backdrop-blur-md">
      <div className="max-w-4xl mx-auto space-y-2">
        {/* Permission / Recording Error Notice */}
        {micError && (
          <div className="flex items-center justify-between gap-2 p-2.5 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-xs">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{micError}</span>
            </div>
            <button
              onClick={() => setMicError(null)}
              className="text-rose-400 hover:text-rose-200 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        <div className="relative flex items-end gap-2 p-2 rounded-xl border border-slate-800 bg-slate-900/80 focus-within:border-indigo-500/60 focus-within:ring-1 focus-within:ring-indigo-500/30 transition-all shadow-inner">
          {/* Active Voice Recording Overlay */}
          {isRecording ? (
            <div className="flex-1 flex items-center justify-between py-1.5 px-3 bg-slate-950/70 rounded-lg border border-red-500/30">
              <div className="flex items-center gap-3">
                <span className="flex h-3 w-3 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
                </span>
                <span className="text-xs font-medium text-red-300">Recording speech...</span>
                <span className="text-xs font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                  {formatSeconds(recordSeconds)}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleCancelRecording}
                  className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer text-xs flex items-center gap-1"
                  title="Cancel recording"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Cancel</span>
                </button>
                <button
                  type="button"
                  onClick={handleStopRecordingAndTranscribe}
                  className="px-2.5 py-1 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition-colors cursor-pointer text-xs flex items-center gap-1 shadow-sm"
                  title="Finish recording"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Done</span>
                </button>
              </div>
            </div>
          ) : isTranscribing ? (
            <div className="flex-1 flex items-center gap-2 py-2 px-3 text-xs text-indigo-300">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Transcribing your speech to text...</span>
            </div>
          ) : (
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              placeholder={
                disabled
                  ? 'Provider not configured. Please set up OpenRouter API key in Settings.'
                  : placeholder
              }
              rows={1}
              className="flex-1 bg-transparent border-0 focus:ring-0 text-sm text-slate-100 placeholder-slate-500 resize-none py-1.5 px-2 outline-none max-h-44 disabled:opacity-50"
            />
          )}

          {/* Action Buttons: Microphone & Send/Stop */}
          <div className="shrink-0 flex items-center gap-1 pb-0.5">
            {!isRecording && !isTranscribing && (
              <button
                type="button"
                onClick={handleStartRecording}
                disabled={disabled || isStreaming}
                className="p-2 rounded-lg text-slate-400 hover:text-indigo-400 hover:bg-slate-800 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                title="Speak to Assistant (Record speech)"
              >
                <Mic className="w-4 h-4" />
              </button>
            )}

            {isStreaming ? (
              <button
                type="button"
                onClick={onStopGeneration}
                className="p-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white transition-colors cursor-pointer shadow-sm"
                title="Stop generation"
              >
                <Square className="w-4 h-4 fill-white" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={!input.trim() || disabled || isRecording || isTranscribing}
                className="p-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
                title="Send message"
              >
                <Send className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500 px-1">
          <span>Responses stream in real-time. Speak or type naturally.</span>
          <span>OpenRouter &bull; Voice AI</span>
        </div>
      </div>
    </div>
  );
};

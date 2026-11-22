import React, { useState, useRef, useEffect } from 'react';
import { Send, Square } from 'lucide-react';

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
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

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

  return (
    <div className="p-4 bg-slate-950/90 border-t border-slate-800 backdrop-blur-md">
      <div className="max-w-4xl mx-auto">
        <div className="relative flex items-end gap-2 p-2 rounded-xl border border-slate-800 bg-slate-900/80 focus-within:border-indigo-500/60 focus-within:ring-1 focus-within:ring-indigo-500/30 transition-all shadow-inner">
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

          <div className="shrink-0 flex items-center pb-0.5">
            {isStreaming ? (
              <button
                onClick={onStopGeneration}
                className="p-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white transition-colors cursor-pointer shadow-sm"
                title="Stop generation"
              >
                <Square className="w-4 h-4 fill-white" />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={!input.trim() || disabled}
                className="p-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
                title="Send message"
              >
                <Send className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500 px-1">
          <span>Responses stream in real-time from active provider.</span>
          <span>OpenRouter &bull; Single-user</span>
        </div>
      </div>
    </div>
  );
};

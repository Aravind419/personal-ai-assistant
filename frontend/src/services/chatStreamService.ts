import { env } from '../config/env';

export interface StreamDoneResult {
  message_id: string;
  content: string;
  model: string;
  estimated_cost_usd?: number;
  pricing_category?: string;
  latency_ms?: number;
  fallback_used?: boolean;
}

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onDone: (result: StreamDoneResult) => void;
  onError: (error: string) => void;
  onNotice?: (notice: string) => void;
}

/**
 * Consumes Server-Sent Events (SSE) streaming chat completions from the FastAPI backend.
 */
export async function streamChatMessage(
  conversationId: string,
  content: string,
  callbacks: StreamCallbacks,
  options?: {
    model?: string;
    systemPrompt?: string;
    signal?: AbortSignal;
  }
): Promise<void> {
  const url = `${env.apiBaseUrl}/conversations/${conversationId}/messages`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({
        content,
        model: options?.model,
        system_prompt: options?.systemPrompt,
      }),
      signal: options?.signal,
    });

    if (!response.ok) {
      let errText = `HTTP ${response.status} ${response.statusText}`;
      try {
        const errJson = await response.json();
        if (errJson.error?.message) {
          errText = errJson.error.message;
        } else if (errJson.detail) {
          errText = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
        }
      } catch {
        // Fall back to default
      }
      callbacks.onError(errText);
      return;
    }

    if (!response.body) {
      callbacks.onError('ReadableStream not supported in response body.');
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data: ')) continue;

        const payloadStr = trimmed.slice(6).trim();
        try {
          const payload = JSON.parse(payloadStr);

          if (payload.type === 'token' && typeof payload.delta === 'string') {
            callbacks.onToken(payload.delta);
          } else if (payload.type === 'notice' && typeof payload.message === 'string') {
            callbacks.onNotice?.(payload.message);
          } else if (payload.type === 'error') {
            callbacks.onError(payload.error || payload.message || 'Streaming error');
          } else if (payload.type === 'done') {
            callbacks.onDone({
              message_id: payload.message_id,
              content: payload.content,
              model: payload.model,
              estimated_cost_usd: payload.estimated_cost_usd,
              pricing_category: payload.pricing_category,
              latency_ms: payload.latency_ms,
              fallback_used: payload.fallback_used,
            });
          }
        } catch {
          // Ignore incomplete JSON chunks in transit
        }
      }
    }
  } catch (error: any) {
    if (error.name === 'AbortError') {
      // User aborted stream cleanly
      return;
    }
    callbacks.onError(error.message || 'Network communication error during streaming.');
  }
}

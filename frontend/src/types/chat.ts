export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  model?: string | null;
  provider?: string | null;
  tokens_prompt?: number | null;
  tokens_completion?: number | null;
  created_at: string;
  isStreaming?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  provider_type: string;
  model: string;
  system_prompt?: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface ConversationSummary {
  id: string;
  title: string;
  provider_type: string;
  model: string;
  is_archived: boolean;
  message_count: number;
  last_message_preview?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationCreate {
  title?: string;
  provider_type?: string;
  model?: string;
  system_prompt?: string;
}

export interface ConversationUpdate {
  title?: string;
  model?: string;
  system_prompt?: string;
  is_archived?: boolean;
}

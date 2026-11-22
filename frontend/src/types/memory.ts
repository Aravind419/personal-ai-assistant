export interface MemoryItem {
  id: string;
  content: string;
  category: string;
  importance: number;
  confidence: number;
  source_conversation_id?: string | null;
  source_message_id?: string | null;
  last_accessed_at?: string | null;
  expires_at?: string | null;
  is_archived: boolean;
  embedding_model: string;
  embedding_dim: number;
  metadata_json?: string | null;
  metadata?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryListResponse {
  items: MemoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface MemorySearchResult {
  memory: MemoryItem;
  similarity_score: number;
  relevance_score: number;
}

export interface MemoryStats {
  total_active: number;
  total_archived: number;
  category_distribution: Record<string, number>;
  recent_memories: MemoryItem[];
}

export interface MemoryCreatePayload {
  content: string;
  category?: string;
  importance?: number;
  confidence?: number;
  source_conversation_id?: string | null;
  source_message_id?: string | null;
  metadata?: Record<string, any> | null;
}

export interface MemoryUpdatePayload {
  content?: string;
  category?: string;
  importance?: number;
  confidence?: number;
  is_archived?: boolean;
  metadata?: Record<string, any> | null;
}

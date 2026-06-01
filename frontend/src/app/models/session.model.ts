export type SessionStatus = 'active' | 'escalated' | 'closed';

export interface SessionListItem {
  id: string;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
  last_message_preview: string | null;
  message_count: number;
}

export interface SessionListResponse {
  items: SessionListItem[];
  next_cursor: string | null;
}

export interface RawMessage {
  id: string;
  role: 'user' | 'assistant' | 'tool' | string;
  content: string | RawContentBlock[] | Record<string, unknown>;
  created_at: string;
}

export type RawContentBlock =
  | { type: 'text'; text: string }
  | { type: 'tool_use'; id: string; name: string; input: Record<string, unknown> }
  | { type: 'tool_result'; tool_use_id: string; content: unknown };

export interface SessionDetail {
  id: string;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown> | null;
  messages: RawMessage[];
}

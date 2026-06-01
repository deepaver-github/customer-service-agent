export interface ToolCall {
  id: string;
  name: string;
  status: 'running' | 'done' | 'error';
  input?: Record<string, unknown>;
  result?: unknown;
}

export interface UserTurn {
  kind: 'user';
  id: string;
  text: string;
  timestamp: string;
}

export interface AssistantTurn {
  kind: 'assistant';
  id: string;
  text: string;
  toolCalls: ToolCall[];
  timestamp: string;
  isStreaming?: boolean;
}

export interface EscalationMarker {
  kind: 'escalation';
  id: string;
  reason?: string;
  timestamp: string;
}

export type DisplayTurn = UserTurn | AssistantTurn | EscalationMarker;

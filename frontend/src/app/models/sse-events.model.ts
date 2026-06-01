/** SSE event payloads emitted by POST /chat/stream. Mirrors the backend. */

export interface StreamStartEvent { session_id: string; }
export interface TextDeltaEvent { delta: string; }
export interface ToolStartEvent { tool_name: string; tool_use_id: string; }
export interface ToolResultEvent { tool_name: string; tool_use_id: string; result: unknown; }
export interface EscalationEvent { reason: string; }
export interface DoneEvent {
  response: string;
  session_id: string;
  escalated: boolean;
  tools_used: string[];
}
export interface ErrorEvent { error: string; }

export type SseEventName =
  | 'stream_start'
  | 'text_delta'
  | 'tool_start'
  | 'tool_result'
  | 'escalation'
  | 'done'
  | 'error';

export interface ParsedSseEvent {
  event: SseEventName;
  data:
    | StreamStartEvent
    | TextDeltaEvent
    | ToolStartEvent
    | ToolResultEvent
    | EscalationEvent
    | DoneEvent
    | ErrorEvent;
}

import { Injectable } from '@angular/core';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import {
  DoneEvent,
  ErrorEvent,
  EscalationEvent,
  ParsedSseEvent,
  SseEventName,
  StreamStartEvent,
  TextDeltaEvent,
  ToolResultEvent,
  ToolStartEvent,
} from '../models/sse-events.model';

export interface StreamCallbacks {
  onStart: (e: StreamStartEvent) => void;
  onTextDelta: (e: TextDeltaEvent) => void;
  onToolStart: (e: ToolStartEvent) => void;
  onToolResult: (e: ToolResultEvent) => void;
  onEscalation: (e: EscalationEvent) => void;
  onDone: (e: DoneEvent) => void;
  onError: (e: ErrorEvent | { error: string }) => void;
}

@Injectable({ providedIn: 'root' })
export class ChatService {
  private currentAbort: AbortController | null = null;

  /** Start a streaming chat request. Returns an AbortController the caller can use. */
  async streamMessage(
    body: { message: string; session_id?: string | null },
    callbacks: StreamCallbacks,
  ): Promise<void> {
    this.cancel();
    const ctrl = new AbortController();
    this.currentAbort = ctrl;

    try {
      await fetchEventSource('/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify(body),
        signal: ctrl.signal,
        openWhenHidden: true,
        onopen: async (resp) => {
          if (!resp.ok) {
            const text = await resp.text().catch(() => '');
            throw new Error(`HTTP ${resp.status}: ${text || resp.statusText}`);
          }
        },
        onmessage: (msg) => {
          const event = (msg.event || 'message') as SseEventName;
          let data: ParsedSseEvent['data'];
          try {
            data = JSON.parse(msg.data || '{}');
          } catch {
            return;
          }
          switch (event) {
            case 'stream_start':
              callbacks.onStart(data as StreamStartEvent);
              break;
            case 'text_delta':
              callbacks.onTextDelta(data as TextDeltaEvent);
              break;
            case 'tool_start':
              callbacks.onToolStart(data as ToolStartEvent);
              break;
            case 'tool_result':
              callbacks.onToolResult(data as ToolResultEvent);
              break;
            case 'escalation':
              callbacks.onEscalation(data as EscalationEvent);
              break;
            case 'done':
              callbacks.onDone(data as DoneEvent);
              break;
            case 'error':
              callbacks.onError(data as ErrorEvent);
              break;
          }
        },
        onerror: (err) => {
          callbacks.onError({ error: err?.message || 'connection error' });
          // throw to stop reconnection attempts
          throw err;
        },
        onclose: () => {
          // close is fine; done event fires before this normally
        },
      });
    } catch (err: unknown) {
      if (ctrl.signal.aborted) return;
      const message = err instanceof Error ? err.message : String(err);
      callbacks.onError({ error: message });
    } finally {
      if (this.currentAbort === ctrl) this.currentAbort = null;
    }
  }

  cancel(): void {
    if (this.currentAbort) {
      this.currentAbort.abort();
      this.currentAbort = null;
    }
  }
}

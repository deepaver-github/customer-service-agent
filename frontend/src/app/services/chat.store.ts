import { Injectable, computed, inject, signal } from '@angular/core';
import {
  AssistantTurn,
  DisplayTurn,
  EscalationMarker,
  ToolCall,
  UserTurn,
} from '../models/chat.model';
import {
  RawContentBlock,
  RawMessage,
  SessionListItem,
} from '../models/session.model';
import { ChatService } from './chat.service';
import { SessionService } from './session.service';

let displayIdCounter = 0;
const nextId = (prefix: string) => `${prefix}-${++displayIdCounter}-${Date.now()}`;

@Injectable({ providedIn: 'root' })
export class ChatStore {
  private chat = inject(ChatService);
  private sessions_ = inject(SessionService);

  /* ============ State ============ */
  readonly sessions = signal<SessionListItem[]>([]);
  readonly sessionsCursor = signal<string | null>(null);
  readonly sessionsLoading = signal<boolean>(false);

  readonly currentSessionId = signal<string | null>(null);
  readonly turns = signal<DisplayTurn[]>([]);
  readonly isStreaming = signal<boolean>(false);
  readonly isEscalated = signal<boolean>(false);

  /** Title of the current session, derived from sessions list or first user turn. */
  readonly currentTitle = computed(() => {
    const id = this.currentSessionId();
    if (!id) return 'New conversation';
    const item = this.sessions().find((s) => s.id === id);
    if (item?.last_message_preview) return item.last_message_preview;
    const first = this.turns().find((t) => t.kind === 'user') as UserTurn | undefined;
    return first?.text || 'New conversation';
  });

  /* ============ Sessions list ============ */
  async loadSessions(): Promise<void> {
    if (this.sessionsLoading()) return;
    this.sessionsLoading.set(true);
    try {
      const resp = await this.sessions_.list(null, 30);
      this.sessions.set(resp.items);
      this.sessionsCursor.set(resp.next_cursor);
    } finally {
      this.sessionsLoading.set(false);
    }
  }

  async loadMoreSessions(): Promise<void> {
    const cursor = this.sessionsCursor();
    if (!cursor || this.sessionsLoading()) return;
    this.sessionsLoading.set(true);
    try {
      const resp = await this.sessions_.list(cursor, 30);
      this.sessions.update((prev) => [...prev, ...resp.items]);
      this.sessionsCursor.set(resp.next_cursor);
    } finally {
      this.sessionsLoading.set(false);
    }
  }

  /* ============ Session selection ============ */
  async selectSession(sessionId: string): Promise<void> {
    if (this.currentSessionId() === sessionId) return;
    this.chat.cancel();
    this.currentSessionId.set(sessionId);
    this.turns.set([]);
    this.isStreaming.set(false);
    const detail = await this.sessions_.get(sessionId);
    this.isEscalated.set(detail.status === 'escalated');
    this.turns.set(this.rawToTurns(detail.messages));
  }

  newSession(): void {
    this.chat.cancel();
    this.currentSessionId.set(null);
    this.turns.set([]);
    this.isStreaming.set(false);
    this.isEscalated.set(false);
  }

  /* ============ Sending a message ============ */
  async sendMessage(text: string): Promise<void> {
    const trimmed = text.trim();
    if (!trimmed || this.isStreaming()) return;

    const now = new Date().toISOString();
    const userTurn: UserTurn = { kind: 'user', id: nextId('u'), text: trimmed, timestamp: now };
    const assistantTurn: AssistantTurn = {
      kind: 'assistant',
      id: nextId('a'),
      text: '',
      toolCalls: [],
      timestamp: now,
      isStreaming: true,
    };
    this.turns.update((prev) => [...prev, userTurn, assistantTurn]);
    this.isStreaming.set(true);

    const sessionId = this.currentSessionId();
    await this.chat.streamMessage(
      { message: trimmed, session_id: sessionId },
      {
        onStart: (e) => {
          if (!sessionId) this.currentSessionId.set(e.session_id);
        },
        onTextDelta: (e) => {
          this.updateAssistant(assistantTurn.id, (a) => ({ ...a, text: a.text + e.delta }));
        },
        onToolStart: (e) => {
          this.updateAssistant(assistantTurn.id, (a) => ({
            ...a,
            toolCalls: [
              ...a.toolCalls,
              { id: e.tool_use_id, name: e.tool_name, status: 'running' as const },
            ],
          }));
        },
        onToolResult: (e) => {
          this.updateAssistant(assistantTurn.id, (a) => ({
            ...a,
            toolCalls: a.toolCalls.map((tc) =>
              tc.id === e.tool_use_id
                ? { ...tc, status: 'done' as const, result: e.result }
                : tc,
            ),
          }));
        },
        onEscalation: (e) => {
          this.isEscalated.set(true);
          this.turns.update((prev) => [
            ...prev,
            { kind: 'escalation', id: nextId('e'), reason: e.reason, timestamp: new Date().toISOString() } as EscalationMarker,
          ]);
        },
        onDone: () => {
          this.updateAssistant(assistantTurn.id, (a) => ({ ...a, isStreaming: false }));
          this.isStreaming.set(false);
          // refresh sessions list silently so sidebar reflects latest activity
          this.loadSessions().catch(() => {});
        },
        onError: (e) => {
          this.updateAssistant(assistantTurn.id, (a) => ({
            ...a,
            text: a.text || `(connection error: ${e.error})`,
            isStreaming: false,
          }));
          this.isStreaming.set(false);
        },
      },
    );
  }

  /* ============ Helpers ============ */
  private updateAssistant(id: string, fn: (a: AssistantTurn) => AssistantTurn): void {
    this.turns.update((prev) =>
      prev.map((t) => (t.kind === 'assistant' && t.id === id ? fn(t) : t)),
    );
  }

  /** Convert backend RawMessage[] into display turns, joining tool_use + tool_result. */
  private rawToTurns(raw: RawMessage[]): DisplayTurn[] {
    const turns: DisplayTurn[] = [];
    // Track tool calls by id across the assistant + following tool messages so results can be attached.
    let lastAssistant: AssistantTurn | null = null;

    for (const m of raw) {
      if (m.role === 'user') {
        const text = typeof m.content === 'string' ? m.content : this.flattenText(m.content);
        turns.push({
          kind: 'user',
          id: m.id,
          text: text || '(empty)',
          timestamp: m.created_at,
        });
        lastAssistant = null;
      } else if (m.role === 'assistant') {
        const { text, toolCalls } = this.extractAssistant(m.content);
        const turn: AssistantTurn = {
          kind: 'assistant',
          id: m.id,
          text,
          toolCalls,
          timestamp: m.created_at,
        };
        turns.push(turn);
        lastAssistant = turn;
      } else if (m.role === 'tool' || m.role === 'user_with_tool_result') {
        // tool_result message: attach to lastAssistant's matching tool call
        if (lastAssistant && Array.isArray(m.content)) {
          const updatedTools = [...lastAssistant.toolCalls];
          for (const block of m.content as RawContentBlock[]) {
            if (block.type === 'tool_result') {
              const idx = updatedTools.findIndex((tc) => tc.id === block.tool_use_id);
              if (idx >= 0) {
                updatedTools[idx] = { ...updatedTools[idx], status: 'done', result: block.content };
              }
            }
          }
          const replaced: AssistantTurn = { ...lastAssistant, toolCalls: updatedTools };
          const i = turns.indexOf(lastAssistant);
          if (i >= 0) turns[i] = replaced;
          lastAssistant = replaced;
        }
      }
    }
    return turns;
  }

  private extractAssistant(content: RawMessage['content']): { text: string; toolCalls: ToolCall[] } {
    if (typeof content === 'string') return { text: content, toolCalls: [] };
    if (!Array.isArray(content)) return { text: '', toolCalls: [] };
    let text = '';
    const toolCalls: ToolCall[] = [];
    for (const block of content as RawContentBlock[]) {
      if (block.type === 'text') {
        text += (text ? '\n\n' : '') + block.text;
      } else if (block.type === 'tool_use') {
        toolCalls.push({
          id: block.id,
          name: block.name,
          status: 'done',
          input: block.input,
        });
      }
    }
    return { text, toolCalls };
  }

  private flattenText(content: RawMessage['content']): string {
    if (typeof content === 'string') return content;
    if (Array.isArray(content)) {
      return (content as RawContentBlock[])
        .filter((b): b is { type: 'text'; text: string } => b.type === 'text')
        .map((b) => b.text)
        .join(' ');
    }
    return '';
  }
}

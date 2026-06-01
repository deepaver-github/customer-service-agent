import { Component, computed, input } from '@angular/core';
import { DisplayTurn } from '../../models/chat.model';
import { renderMarkdown } from '../../utils/markdown.util';
import { formatTime } from '../../utils/timeago.util';
import { ToolCardComponent } from '../tool-card/tool-card';

@Component({
  selector: 'app-message-item',
  standalone: true,
  imports: [ToolCardComponent],
  template: `
    @switch (turn().kind) {
      @case ('user') {
        <div class="flex flex-col gap-1.5">
          <div class="flex items-center gap-2 text-xs text-ink-500">
            <div class="flex h-[22px] w-[22px] flex-shrink-0 items-center justify-center
                        rounded-md bg-ink-900 text-[10px] font-bold text-white">
              {{ initials() }}
            </div>
            <span class="font-semibold text-ink-700">You</span>
            <span class="text-ink-400">· {{ time() }}</span>
          </div>
          <div class="ml-[30px] inline-block self-start rounded-2xl border border-user-border
                      bg-user-tint px-4 py-3 text-[15.5px] leading-relaxed text-ink-900 prose-msg"
               [innerHTML]="rendered()"></div>
        </div>
      }
      @case ('assistant') {
        <div class="flex flex-col gap-1.5">
          <div class="flex items-center gap-2 text-xs text-ink-500">
            <div class="flex h-[22px] w-[22px] flex-shrink-0 items-center justify-center
                        rounded-md bg-gradient-to-br from-accent to-indigo-400
                        font-display text-[10px] font-bold text-white">
              A
            </div>
            <span class="font-semibold text-ink-700">Aria</span>
            <span class="text-ink-400">· {{ time() }}</span>
          </div>
          @for (call of toolCalls(); track call.id) {
            <app-tool-card [call]="call"></app-tool-card>
          }
          @if (assistantText()) {
            <div class="pl-[30px] text-[15.5px] leading-relaxed text-ink-900 prose-msg"
                 [innerHTML]="rendered()"></div>
          }
          @if (showCaret()) {
            <span aria-hidden="true"
                  class="ml-[30px] inline-block h-[1.1em] w-[2px] animate-blink rounded-sm
                         bg-accent align-text-bottom"></span>
          }
        </div>
      }
      @case ('escalation') {
        <div class="flex items-start gap-3 rounded-md border border-escalation-border
                    bg-escalation-bg px-4 py-3 text-[14px] leading-snug text-escalation-text">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round"
               class="mt-0.5 h-4 w-4 flex-shrink-0">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <div>
            <strong class="block font-semibold">This conversation has been escalated</strong>
            A senior support specialist will join shortly. Aria stays connected and can keep helping in the meantime.
          </div>
        </div>
      }
    }
  `,
})
export class MessageItemComponent {
  turn = input.required<DisplayTurn>();
  userInitials = input<string>('You');

  readonly time = computed(() => formatTime(this.turn().timestamp));
  readonly initials = computed(() => {
    const v = this.userInitials();
    return v.slice(0, 2).toUpperCase();
  });
  readonly assistantText = computed(() => {
    const t = this.turn();
    return t.kind === 'assistant' ? t.text : '';
  });
  readonly userText = computed(() => {
    const t = this.turn();
    return t.kind === 'user' ? t.text : '';
  });
  readonly toolCalls = computed(() => {
    const t = this.turn();
    return t.kind === 'assistant' ? t.toolCalls : [];
  });
  readonly showCaret = computed(() => {
    const t = this.turn();
    return t.kind === 'assistant' && !!t.isStreaming;
  });
  readonly rendered = computed(() => {
    const t = this.turn();
    if (t.kind === 'user') return renderMarkdown(t.text);
    if (t.kind === 'assistant') return renderMarkdown(t.text);
    return '';
  });
}

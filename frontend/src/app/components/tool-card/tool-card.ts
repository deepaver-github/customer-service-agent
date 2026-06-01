import { Component, computed, input, signal } from '@angular/core';
import { ToolCall } from '../../models/chat.model';

@Component({
  selector: 'app-tool-card',
  standalone: true,
  template: `
    <div
      class="my-2 ml-[30px] max-w-[560px] overflow-hidden rounded-md border border-tool-border bg-white text-[13.5px]"
      [class.opacity-90]="call().status === 'running'"
    >
      <button
        type="button"
        class="flex w-full select-none items-center gap-2 border-b border-tool-border bg-tool-bg px-3 py-[9px] text-left"
        [class.border-b-0]="!isExpanded()"
        (click)="toggle()"
        [attr.aria-expanded]="isExpanded()"
      >
        <span
          class="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full"
          [class]="statusBg()"
        >
          @if (call().status === 'running') {
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-linecap="round" stroke-linejoin="round" stroke-width="3"
              class="h-2.5 w-2.5 animate-spinslow">
              <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
            </svg>
          } @else {
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-linecap="round" stroke-linejoin="round" stroke-width="3"
              class="h-2.5 w-2.5">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          }
        </span>
        <span class="text-[12.5px] text-ink-500">
          {{ call().status === 'running' ? 'Running' : 'Used' }}
        </span>
        <span class="font-mono text-[12.5px] font-medium text-ink-900">
          {{ call().name }}
        </span>
        <span class="ml-auto text-ink-400 transition-transform"
          [class.rotate-180]="isExpanded()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
            stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
            class="h-3.5 w-3.5">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </span>
      </button>
      @if (isExpanded()) {
        <div class="bg-white px-3.5 py-3">
          @if (call().result !== undefined) {
            <pre class="overflow-x-auto whitespace-pre rounded border border-ink-200 bg-ink-100 px-3 py-2.5 font-mono text-[12.5px] leading-relaxed text-ink-700">{{ formatResult() }}</pre>
          } @else {
            <div class="text-[12.5px] italic text-ink-500">
              {{ call().status === 'running' ? 'Awaiting result…' : 'No result captured.' }}
            </div>
          }
        </div>
      }
    </div>
  `,
})
export class ToolCardComponent {
  call = input.required<ToolCall>();
  private expanded = signal<boolean>(false);

  readonly isExpanded = computed(() => this.expanded());
  readonly statusBg = computed(() =>
    this.call().status === 'running'
      ? 'bg-accent-soft text-accent'
      : 'bg-green-100 text-green-600',
  );

  toggle() { this.expanded.update((v) => !v); }

  formatResult(): string {
    const r = this.call().result;
    if (r === undefined || r === null) return '';
    if (typeof r === 'string') return r;
    try { return JSON.stringify(r, null, 2); }
    catch { return String(r); }
  }
}

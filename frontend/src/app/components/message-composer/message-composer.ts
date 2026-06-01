import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';

@Component({
  selector: 'app-message-composer',
  standalone: true,
  template: `
    <div class="bg-surface px-7 pb-6 pt-4 md:px-7">
      <div class="mx-auto flex max-w-thread items-end gap-2 rounded-composer border border-ink-200
                  bg-white py-2 pl-[18px] pr-2 shadow-composer transition focus-within:border-accent
                  focus-within:shadow-[0_0_0_4px_rgba(30,126,45,0.18),0_4px_12px_rgba(24,24,27,0.06)]">
        <textarea
          #ta
          [value]="value()"
          (input)="onInput($event)"
          (keydown)="onKey($event)"
          [disabled]="disabled()"
          [placeholder]="placeholder()"
          rows="1"
          class="max-h-[160px] flex-1 resize-none border-0 bg-transparent py-2.5 text-[15px] leading-snug
                 outline-none placeholder:text-ink-400 disabled:opacity-60"
        ></textarea>
        <div class="flex items-center gap-1">
          <button
            type="button"
            class="flex h-[38px] w-[38px] items-center justify-center rounded-full text-ink-500
                   transition hover:bg-ink-100 hover:text-ink-900"
            aria-label="Attach file"
            disabled
            title="Attachments coming soon"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round" class="h-[18px] w-[18px]">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
            </svg>
          </button>
          <button
            type="button"
            class="flex h-[38px] w-[38px] items-center justify-center rounded-full bg-accent text-white
                   shadow-send transition hover:-translate-y-px hover:bg-accent-hover
                   disabled:translate-y-0 disabled:cursor-not-allowed disabled:bg-ink-300 disabled:shadow-none"
            [disabled]="disabled() || !canSend()"
            (click)="submit()"
            [attr.aria-label]="disabled() ? 'Streaming…' : 'Send message'"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"
                 stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
              <line x1="12" y1="19" x2="12" y2="5"/>
              <polyline points="5 12 12 5 19 12"/>
            </svg>
          </button>
        </div>
      </div>
      <div class="mx-auto mt-2 max-w-thread text-center text-[11.5px] text-ink-400">
        Press <kbd class="rounded border border-ink-200 bg-ink-100 px-1.5 py-px font-mono text-[10.5px] text-ink-700">Enter</kbd> to send ·
        <kbd class="rounded border border-ink-200 bg-ink-100 px-1.5 py-px font-mono text-[10.5px] text-ink-700">Shift</kbd>
        + <kbd class="rounded border border-ink-200 bg-ink-100 px-1.5 py-px font-mono text-[10.5px] text-ink-700">Enter</kbd> for newline ·
        Your Care Assistant can make mistakes — verify important info
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MessageComposerComponent {
  disabled = input<boolean>(false);
  placeholder = input<string>('Message Special Care Australia…');
  send = output<string>();

  protected value = signal<string>('');
  private ta = viewChild<ElementRef<HTMLTextAreaElement>>('ta');

  canSend(): boolean {
    return this.value().trim().length > 0;
  }

  onInput(ev: Event) {
    const t = ev.target as HTMLTextAreaElement;
    this.value.set(t.value);
    this.autosize(t);
  }

  onKey(ev: KeyboardEvent) {
    if (ev.key === 'Enter' && !ev.shiftKey && !ev.isComposing) {
      ev.preventDefault();
      this.submit();
    }
  }

  submit() {
    if (this.disabled() || !this.canSend()) return;
    const text = this.value().trim();
    this.send.emit(text);
    this.value.set('');
    const el = this.ta()?.nativeElement;
    if (el) {
      el.value = '';
      el.style.height = 'auto';
      el.focus();
    }
  }

  private autosize(el: HTMLTextAreaElement) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }
}

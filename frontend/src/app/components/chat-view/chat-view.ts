import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  effect,
  ElementRef,
  inject,
  viewChild,
} from '@angular/core';
import { ChatStore } from '../../services/chat.store';
import { MessageItemComponent } from '../message-item/message-item';
import { MessageComposerComponent } from '../message-composer/message-composer';

@Component({
  selector: 'app-chat-view',
  standalone: true,
  imports: [MessageItemComponent, MessageComposerComponent],
  template: `
    <div class="flex h-full min-w-0 flex-1 flex-col bg-surface">
      <header class="flex items-center gap-3.5 border-b border-ink-200
                     bg-surface/85 px-7 py-3.5 backdrop-blur supports-[backdrop-filter]:bg-surface/60">
        <button
          type="button"
          class="flex h-9 w-9 items-center justify-center rounded-lg text-ink-700
                 hover:bg-surface-hover md:hidden"
          aria-label="Open conversations"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round" class="h-[18px] w-[18px]">
            <line x1="3" y1="6" x2="21" y2="6"/>
            <line x1="3" y1="12" x2="21" y2="12"/>
            <line x1="3" y1="18" x2="21" y2="18"/>
          </svg>
        </button>
        <div class="flex-1 overflow-hidden text-ellipsis whitespace-nowrap font-display
                    text-[17px] font-semibold tracking-tight">
          {{ store.currentTitle() }}
        </div>
        @if (store.isEscalated()) {
          <span class="inline-flex items-center gap-1.5 rounded-full bg-escalation-bg
                       px-2.5 py-1 text-xs font-medium text-escalation-text">
            <span class="h-1.5 w-1.5 rounded-full bg-escalation-border"></span>
            Escalated
          </span>
        } @else {
          <span class="inline-flex items-center gap-1.5 rounded-full bg-green-100
                       px-2.5 py-1 text-xs font-medium text-green-800">
            <span class="h-1.5 w-1.5 rounded-full bg-green-600 ring-2 ring-green-600/20"></span>
            Active
          </span>
        }
      </header>

      <div
        #thread
        class="scroll-polish flex-1 overflow-y-auto px-7 pb-6 pt-8"
        role="log"
        aria-live="polite"
        (scroll)="onScroll()"
      >
        <div class="mx-auto flex max-w-thread flex-col gap-7">
          @for (turn of store.turns(); track turn.id) {
            <app-message-item [turn]="turn"></app-message-item>
          } @empty {
            <div class="mx-auto mt-16 max-w-md text-center">
              <img src="logo.png" alt="Special Care Australia"
                   class="mx-auto mb-6 h-24 w-auto max-w-[260px] object-contain" />
              <h2 class="mb-2 font-display text-2xl font-semibold tracking-tight text-ink-900">
                How can I help you today?
              </h2>
              <p class="text-[14px] text-ink-500">
                Ask about your supports, plan, services, or anything else.
                I can look things up and connect you with our team when needed.
              </p>
            </div>
          }
        </div>
      </div>

      <app-message-composer
        [disabled]="store.isStreaming()"
        (send)="onSend($event)"
      ></app-message-composer>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChatViewComponent implements AfterViewInit {
  store = inject(ChatStore);
  private thread = viewChild<ElementRef<HTMLDivElement>>('thread');
  private stickToBottom = true;

  constructor() {
    // When turns change while the user is at the bottom, scroll down.
    effect(() => {
      this.store.turns();
      this.store.isStreaming();
      if (!this.stickToBottom) return;
      queueMicrotask(() => this.scrollToBottom('auto'));
    });
  }

  ngAfterViewInit(): void {
    this.scrollToBottom('auto');
  }

  onScroll() {
    const el = this.thread()?.nativeElement;
    if (!el) return;
    const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
    this.stickToBottom = dist < 80;
  }

  onSend(text: string) {
    this.stickToBottom = true;
    this.store.sendMessage(text);
  }

  private scrollToBottom(behavior: ScrollBehavior) {
    const el = this.thread()?.nativeElement;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
  }
}

import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ChatStore } from '../../services/chat.store';
import { SessionListItem } from '../../models/session.model';
import { dayBucket, timeAgo } from '../../utils/timeago.util';

interface Group {
  label: 'Today' | 'Yesterday' | 'Earlier';
  items: SessionListItem[];
}

@Component({
  selector: 'app-session-list',
  standalone: true,
  template: `
    <aside class="hidden h-full w-[280px] flex-shrink-0 flex-col border-r border-ink-200
                  bg-surface-sidebar md:flex">
      <div class="flex items-center gap-2.5 px-[18px] pb-3.5 pt-5">
        <img src="favicon.png" alt="Special Care Australia"
             class="h-9 w-9 flex-shrink-0 object-contain" />
        <div class="min-w-0">
          <div class="overflow-hidden text-ellipsis whitespace-nowrap font-display text-[15px]
                      font-semibold leading-tight tracking-tight text-brand-green">
            Special Care Australia
          </div>
          <div class="mt-px text-[11px] uppercase tracking-wider text-ink-500">NDIS Support</div>
        </div>
      </div>

      <div class="px-3.5 pb-3 pt-1.5">
        <div class="relative">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round"
               class="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-400">
            <circle cx="11" cy="11" r="7"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            type="text"
            placeholder="Search conversations"
            [value]="searchQuery()"
            (input)="onSearchInput($event)"
            class="w-full rounded-md border border-ink-200 bg-white py-2 pl-8 pr-2.5 text-[13px]
                   outline-none transition placeholder:text-ink-400
                   focus:border-accent focus:ring-2 focus:ring-accent-soft"
          />
          @if (searchQuery()) {
            <button
              type="button"
              (click)="clearSearch()"
              aria-label="Clear search"
              class="absolute right-1.5 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center
                     rounded text-ink-400 transition hover:bg-surface-hover hover:text-ink-700"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                   stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          }
        </div>
      </div>

      <div class="scroll-polish flex-1 overflow-y-auto px-2 pb-2">
        @for (group of grouped(); track group.label) {
          <div class="mt-2.5">
            <div class="px-2.5 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-ink-500">
              {{ group.label }}
            </div>
            @for (s of group.items; track s.id) {
              <button
                type="button"
                class="mb-0.5 block w-full rounded-md px-3 py-2.5 text-left transition hover:bg-surface-hover"
                [class.bg-accent-soft]="s.id === store.currentSessionId()"
                (click)="store.selectSession(s.id)"
              >
                <div
                  class="overflow-hidden text-ellipsis whitespace-nowrap text-[13.5px]"
                  [class.font-semibold]="s.id === store.currentSessionId()"
                  [class.text-accent-hover]="s.id === store.currentSessionId()"
                >
                  {{ titleOf(s) }}
                </div>
                @if (s.last_message_preview) {
                  <div class="mt-0.5 overflow-hidden text-ellipsis whitespace-nowrap text-[12px] text-ink-500">
                    {{ s.last_message_preview }}
                  </div>
                }
                <div class="mt-1 flex items-center gap-1.5">
                  <span class="text-[11px] text-ink-400">{{ relativeTime(s.updated_at) }}</span>
                  @if (s.status === 'escalated') {
                    <span class="rounded bg-escalation-bg px-1.5 py-px text-[10px] font-semibold uppercase
                                  tracking-wider text-escalation-text">
                      Escalated
                    </span>
                  }
                </div>
              </button>
            }
          </div>
        } @empty {
          @if (searchQuery()) {
            <div class="px-3 pt-6 text-center text-[13px] text-ink-500">
              No conversations match<br/>“{{ searchQuery() }}”.
            </div>
          } @else {
            <div class="px-3 pt-6 text-center text-[13px] text-ink-500">
              No conversations yet.<br/>Start one below.
            </div>
          }
        }

        @if (store.sessionsCursor() && !searchQuery()) {
          <button
            type="button"
            class="mt-2 w-full rounded-md py-2 text-[12.5px] text-ink-500 transition hover:bg-surface-hover"
            (click)="store.loadMoreSessions()"
            [disabled]="store.sessionsLoading()"
          >
            {{ store.sessionsLoading() ? 'Loading…' : 'Load more' }}
          </button>
        }
      </div>

      <div class="border-t border-ink-200 px-3.5 pb-4 pt-3">
        <button
          type="button"
          class="flex w-full items-center justify-center gap-2 rounded-md bg-ink-900 px-3.5 py-2.5
                 text-[13.5px] font-medium text-white transition hover:bg-accent-hover"
          (click)="store.newSession()"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
               stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          New conversation
        </button>
      </div>
    </aside>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SessionListComponent {
  store = inject(ChatStore);
  readonly searchQuery = signal('');

  private readonly filtered = computed<SessionListItem[]>(() => {
    const q = this.searchQuery().trim().toLowerCase();
    const all = this.store.sessions();
    if (!q) return all;
    return all.filter((s) => {
      const preview = s.last_message_preview?.toLowerCase() ?? '';
      const id = s.id.toLowerCase();
      return preview.includes(q) || id.includes(q);
    });
  });

  readonly grouped = computed<Group[]>(() => {
    const groups: Record<Group['label'], SessionListItem[]> = {
      Today: [], Yesterday: [], Earlier: [],
    };
    for (const s of this.filtered()) {
      groups[dayBucket(s.updated_at)].push(s);
    }
    return (['Today', 'Yesterday', 'Earlier'] as const)
      .map((label) => ({ label, items: groups[label] }))
      .filter((g) => g.items.length > 0);
  });

  onSearchInput(event: Event): void {
    this.searchQuery.set((event.target as HTMLInputElement).value);
  }

  clearSearch(): void {
    this.searchQuery.set('');
  }

  titleOf(s: SessionListItem): string {
    if (s.last_message_preview) {
      const t = s.last_message_preview;
      return t.length > 38 ? t.slice(0, 37).trimEnd() + '…' : t;
    }
    return `Conversation ${s.id.slice(0, 8)}`;
  }

  relativeTime = timeAgo;
}

import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ParticipantListItem, DashboardStats } from '../../models/participant.model';
import { ParticipantService } from '../../services/participant.service';

const STATUSES = ['all', 'active', 'onboarding', 'paused', 'exited'] as const;
type StatusFilter = (typeof STATUSES)[number];

@Component({
  selector: 'app-participant-list',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="flex h-full min-w-0 flex-1 flex-col bg-surface">
      <header class="flex items-center gap-3.5 border-b border-ink-200 bg-surface/85 px-4 py-3 sm:px-7 sm:py-3.5">
        <h1 class="flex-1 font-display text-[17px] font-semibold tracking-tight">Participants</h1>
        <a routerLink="/participants/new"
           class="flex-shrink-0 rounded-md bg-accent px-3.5 py-1.5 text-[13px] font-semibold text-white
                  shadow-send transition hover:bg-accent-hover">
          + New<span class="hidden sm:inline"> participant</span>
        </a>
      </header>

      <div class="scroll-polish flex-1 overflow-y-auto px-4 pb-12 pt-6 sm:px-6 md:px-8">
        <div class="mb-4 flex flex-wrap items-center gap-2.5">
          <div class="relative w-full sm:max-w-[360px] sm:flex-1">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round"
                 class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400">
              <circle cx="11" cy="11" r="7"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              type="text"
              placeholder="Search by name, NDIS number, suburb…"
              [value]="search()"
              (input)="onSearchInput($event)"
              class="w-full rounded-md border border-ink-200 bg-white py-2 pl-9 pr-3 text-[13px]
                     outline-none transition placeholder:text-ink-400
                     focus:border-accent focus:ring-2 focus:ring-accent-soft"
            />
          </div>
          @for (s of statuses; track s) {
            <button
              type="button"
              (click)="status.set(s)"
              class="rounded-md border border-ink-200 px-3 py-1.5 text-[12.5px] transition"
              [class.bg-accent-soft]="status() === s"
              [class.border-accent]="status() === s"
              [class.text-accent-hover]="status() === s"
              [class.font-semibold]="status() === s"
              [class.bg-white]="status() !== s"
              [class.text-ink-700]="status() !== s"
            >
              {{ s.charAt(0).toUpperCase() + s.slice(1) }}
              <span class="ml-1 text-ink-400">·</span>
              <span class="text-ink-500">{{ countFor(s) }}</span>
            </button>
          }
        </div>

        <div class="overflow-hidden rounded-xl border border-ink-200 bg-white">
          <table class="stack-table w-full text-[13.5px]">
            <thead>
              <tr class="border-b border-ink-200 bg-ink-100 text-[11px] font-bold uppercase tracking-wider text-ink-500">
                <th class="px-5 py-2.5 text-left">Participant</th>
                <th class="px-5 py-2.5 text-left">NDIS #</th>
                <th class="px-5 py-2.5 text-left">Status</th>
                <th class="px-5 py-2.5 text-left">Plan management</th>
                <th class="px-5 py-2.5 text-left">Primary contact</th>
              </tr>
            </thead>
            <tbody>
              @for (p of filtered(); track p.id) {
                <tr [routerLink]="['/participants', p.id]"
                    class="cursor-pointer border-b border-ink-100 last:border-b-0
                           transition hover:bg-accent-soft/30">
                  <td class="px-5 py-3.5">
                    <div class="flex items-center gap-2.5">
                      <div class="flex h-9 w-9 items-center justify-center rounded-full
                                  bg-accent-soft text-[12px] font-bold text-accent-hover">
                        {{ initials(p) }}
                      </div>
                      <div class="min-w-0">
                        <div class="truncate font-semibold">
                          {{ p.preferred_name || p.first_name }} {{ p.last_name }}
                        </div>
                        <div class="truncate text-[12px] text-ink-500">
                          @if (p.suburb) { {{ p.suburb }} } @else { — }
                          @if (p.state) { {{ p.state }} }
                        </div>
                      </div>
                    </div>
                  </td>
                  <td data-label="NDIS #" class="px-5 py-3.5 font-mono text-[12.5px]">{{ p.ndis_number }}</td>
                  <td data-label="Status" class="px-5 py-3.5">
                    <span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5
                                 text-[10.5px] font-bold uppercase tracking-wider"
                          [class.bg-accent-soft]="p.status === 'active'"
                          [class.text-accent-hover]="p.status === 'active'"
                          [class.bg-brand-teal-soft]="p.status === 'onboarding'"
                          [class.text-brand-teal]="p.status === 'onboarding'"
                          [class.bg-ink-100]="p.status === 'paused' || p.status === 'exited'"
                          [class.text-ink-700]="p.status === 'paused' || p.status === 'exited'">
                      <span class="h-1.5 w-1.5 rounded-full bg-current"></span>
                      {{ p.status }}
                    </span>
                  </td>
                  <td data-label="Plan management" class="px-5 py-3.5 text-[13px]">
                    @if (p.active_plan_management_type) {
                      {{ p.active_plan_management_type.replace('_', '-') }}
                    } @else {
                      <span class="text-ink-400">No active plan</span>
                    }
                  </td>
                  <td data-label="Primary contact" class="px-5 py-3.5 text-[13px]">
                    @if (p.primary_contact_name) {
                      <div>{{ p.primary_contact_name }}</div>
                      <div class="text-[11.5px] text-ink-500">
                        {{ p.primary_contact_relationship }}
                      </div>
                    } @else {
                      <span class="text-ink-400">—</span>
                    }
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="5" class="px-5 py-10 text-center text-[13px] text-ink-500">
                    @if (search()) {
                      No participants match "{{ search() }}".
                    } @else if (loading()) {
                      Loading…
                    } @else {
                      No participants yet.
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ParticipantListComponent implements OnInit {
  private participants = inject(ParticipantService);
  private route = inject(ActivatedRoute);

  readonly statuses = STATUSES;
  readonly search = signal('');
  readonly status = signal<StatusFilter>('all');
  readonly loading = signal(false);
  readonly all = signal<ParticipantListItem[]>([]);
  readonly stats = signal<DashboardStats | null>(null);

  readonly filtered = computed(() => {
    const q = this.search().trim().toLowerCase();
    const s = this.status();
    let items = this.all();
    if (s !== 'all') items = items.filter((p) => p.status === s);
    if (q) {
      items = items.filter(
        (p) =>
          p.first_name.toLowerCase().includes(q) ||
          p.last_name.toLowerCase().includes(q) ||
          (p.preferred_name ?? '').toLowerCase().includes(q) ||
          p.ndis_number.includes(q) ||
          (p.suburb ?? '').toLowerCase().includes(q),
      );
    }
    return items;
  });

  countFor(s: StatusFilter): number {
    const all = this.all();
    if (s === 'all') return all.length;
    return all.filter((p) => p.status === s).length;
  }

  async ngOnInit() {
    const initialSearch = this.route.snapshot.queryParamMap.get('search');
    if (initialSearch) this.search.set(initialSearch);
    const initialStatus = this.route.snapshot.queryParamMap.get('status') as StatusFilter | null;
    if (initialStatus && (STATUSES as readonly string[]).includes(initialStatus)) {
      this.status.set(initialStatus);
    }

    this.loading.set(true);
    try {
      const resp = await this.participants.list({ limit: 200 });
      this.all.set(resp.items);
    } finally {
      this.loading.set(false);
    }
  }

  onSearchInput(event: Event) {
    this.search.set((event.target as HTMLInputElement).value);
  }

  initials(p: ParticipantListItem): string {
    return ((p.first_name[0] ?? '') + (p.last_name[0] ?? '')).toUpperCase();
  }
}

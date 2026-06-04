import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { DashboardStats, ParticipantListItem } from '../../models/participant.model';
import { ParticipantService } from '../../services/participant.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="flex h-full min-w-0 flex-1 flex-col bg-surface">
      <header class="flex items-center gap-3.5 border-b border-ink-200 bg-surface/85 px-7 py-3.5">
        <h1 class="flex-1 font-display text-[17px] font-semibold tracking-tight">Dashboard</h1>

        <form (submit)="onSearch($event)" class="relative w-[320px]">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round"
               class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400">
            <circle cx="11" cy="11" r="7"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            #searchInput
            type="text"
            name="search"
            placeholder="Search participants…"
            class="w-full rounded-md border border-ink-200 bg-white py-2 pl-9 pr-3 text-[13px]
                   outline-none transition placeholder:text-ink-400
                   focus:border-accent focus:ring-2 focus:ring-accent-soft"
          />
        </form>

        <a routerLink="/participants/new"
           class="rounded-md bg-accent px-3.5 py-1.5 text-[13px] font-semibold text-white
                  shadow-send transition hover:bg-accent-hover">
          + New participant
        </a>
      </header>

      <div class="scroll-polish flex-1 overflow-y-auto px-8 pb-12 pt-6">
        @if (error(); as e) {
          <div class="mb-6 rounded-xl border border-escalation-text/30 bg-escalation-bg/40 px-5 py-4">
            <h3 class="font-display text-[14px] font-semibold text-escalation-text">Couldn't load dashboard</h3>
            <p class="mt-1 text-[12.5px] text-ink-700">{{ e }}</p>
          </div>
        }

        <!-- Stats grid -->
        <section class="mb-8 grid grid-cols-4 gap-4">
          @for (card of cards(); track card.label) {
            <div class="rounded-xl border border-ink-200 bg-white p-5">
              <div class="text-[11px] font-bold uppercase tracking-wider text-ink-500">
                {{ card.label }}
              </div>
              <div class="mt-1 font-display text-[26px] font-semibold tracking-tight">
                {{ card.value }}
              </div>
              @if (card.hint) {
                <div class="mt-0.5 text-[12px] text-ink-500">{{ card.hint }}</div>
              }
            </div>
          }
        </section>

        <!-- Recent participants -->
        <section class="rounded-xl border border-ink-200 bg-white">
          <div class="flex items-center border-b border-ink-200 px-5 py-3">
            <h2 class="font-display text-[14.5px] font-semibold">Recent participants</h2>
            <a routerLink="/participants"
               class="ml-auto text-[12.5px] font-semibold text-accent-hover hover:underline">
              See all →
            </a>
          </div>

          @if (recent().length === 0 && !loading()) {
            <div class="px-5 py-8 text-center text-[13px] text-ink-500">
              No participants on file yet.
            </div>
          } @else {
            <table class="w-full text-[13.5px]">
              <thead>
                <tr class="border-b border-ink-200 bg-ink-100 text-[11px] font-bold uppercase tracking-wider text-ink-500">
                  <th class="px-5 py-2.5 text-left">Name</th>
                  <th class="px-5 py-2.5 text-left">NDIS #</th>
                  <th class="px-5 py-2.5 text-left">Disability</th>
                  <th class="px-5 py-2.5 text-left">Primary contact</th>
                  <th class="px-5 py-2.5 text-left">Status</th>
                </tr>
              </thead>
              <tbody>
                @for (p of recent(); track p.id) {
                  <tr class="cursor-pointer border-b border-ink-100 transition last:border-b-0 hover:bg-surface"
                      (click)="open(p.id)">
                    <td class="px-5 py-3">
                      <div class="font-semibold">
                        {{ p.preferred_name || p.first_name }} {{ p.last_name }}
                      </div>
                      @if (p.suburb) {
                        <div class="text-[11.5px] text-ink-500">{{ p.suburb }} {{ p.state }}</div>
                      }
                    </td>
                    <td class="px-5 py-3 font-mono text-[12.5px]">{{ p.ndis_number }}</td>
                    <td class="px-5 py-3 text-[13px] capitalize">
                      {{ (p.primary_disability_category || '—').replace('_', ' ') }}
                    </td>
                    <td class="px-5 py-3 text-[13px]">
                      {{ p.primary_contact_name || '—' }}
                    </td>
                    <td class="px-5 py-3">
                      <span class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5
                                   text-[10.5px] font-bold uppercase tracking-wider"
                            [class.bg-accent-soft]="p.status === 'active'"
                            [class.text-accent-hover]="p.status === 'active'"
                            [class.bg-brand-teal-soft]="p.status === 'onboarding'"
                            [class.text-brand-teal]="p.status === 'onboarding'"
                            [class.bg-ink-100]="p.status === 'paused' || p.status === 'exited'"
                            [class.text-ink-700]="p.status === 'paused' || p.status === 'exited'">
                        {{ p.status }}
                      </span>
                    </td>
                  </tr>
                }
                @if (loading()) {
                  <tr><td colspan="5" class="px-5 py-6 text-center text-[13px] text-ink-500">Loading…</td></tr>
                }
              </tbody>
            </table>
          }
        </section>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DashboardComponent implements OnInit {
  private participants = inject(ParticipantService);
  private router = inject(Router);

  readonly stats = signal<DashboardStats | null>(null);
  readonly recent = signal<ParticipantListItem[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  readonly cards = () => {
    const s = this.stats();
    return [
      { label: 'Active participants', value: s?.active_participants ?? '—',
        hint: s ? `${s.onboarding_participants} onboarding` : undefined },
      { label: 'Active plans', value: s?.active_plans ?? '—',
        hint: s ? `${s.draft_plans} draft` : undefined },
      { label: 'Service agreements', value: s?.active_agreements ?? '—',
        hint: s ? `${s.draft_agreements} draft` : undefined },
      { label: 'Conversations today', value: s?.conversations_today ?? '—',
        hint: s ? `${s.escalated_today} escalated` : undefined },
    ];
  };

  async ngOnInit() {
    try {
      const [stats, list] = await Promise.all([
        this.participants.dashboardStats(),
        this.participants.list({ limit: 8 }),
      ]);
      this.stats.set(stats);
      this.recent.set(list.items);
    } catch (err) {
      console.error('dashboard load failed', err);
      this.error.set((err as Error)?.message ?? 'Unknown error');
    } finally {
      this.loading.set(false);
    }
  }

  onSearch(ev: SubmitEvent) {
    ev.preventDefault();
    const form = ev.target as HTMLFormElement;
    const value = (form.elements.namedItem('search') as HTMLInputElement)?.value?.trim();
    this.router.navigate(['/participants'], {
      queryParams: value ? { search: value } : undefined,
    });
  }

  open(id: string) {
    this.router.navigate(['/participants', id]);
  }
}

import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthStore } from '../../services/auth.store';
import { LayoutStore } from '../../services/layout.store';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    @if (layout.navOpen()) {
      <div
        (click)="layout.closeNav()"
        class="fixed inset-0 z-40 bg-ink-900/40 md:hidden"
        aria-hidden="true"
      ></div>
    }
    <aside
      class="fixed inset-y-0 left-0 z-50 flex h-full w-[260px] flex-shrink-0 -translate-x-full
             flex-col border-r border-ink-200 bg-surface-sidebar transition-transform duration-200
             md:static md:z-auto md:translate-x-0"
      [class.translate-x-0]="layout.navOpen()"
    >
      <div class="flex items-center gap-2.5 px-[18px] pb-3.5 pt-5">
        <img src="favicon.png" alt="Special Care Australia"
             class="h-9 w-9 flex-shrink-0 object-contain" />
        <div class="min-w-0">
          <div class="overflow-hidden text-ellipsis whitespace-nowrap font-display text-[15px]
                      font-semibold leading-tight tracking-tight text-brand-green">
            Special Care Australia
          </div>
          <div class="mt-px text-[10.5px] uppercase tracking-wider text-ink-500">Care Assistant</div>
        </div>
        <button
          type="button"
          (click)="layout.closeNav()"
          aria-label="Close menu"
          class="ml-auto flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md
                 text-ink-500 transition hover:bg-surface-hover hover:text-ink-900 md:hidden"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" class="h-4 w-4">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <div class="px-3 pt-2 text-[10.5px] font-bold uppercase tracking-wider text-ink-500">
        <div class="px-2.5 py-1">Workspace</div>
      </div>
      <a routerLink="/" routerLinkActive="bg-accent-soft text-accent-hover font-semibold"
         [routerLinkActiveOptions]="{ exact: true }"
         class="mx-2 my-px flex items-center gap-2.5 rounded-md px-3 py-2 text-[13.5px]
                text-ink-700 transition hover:bg-surface-hover">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
          <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
          <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
        </svg>
        Dashboard
      </a>
      <a routerLink="/chat" routerLinkActive="bg-accent-soft text-accent-hover font-semibold"
         class="mx-2 my-px flex items-center gap-2.5 rounded-md px-3 py-2 text-[13.5px]
                text-ink-700 transition hover:bg-surface-hover">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
        Care Assistant
      </a>

      <div class="px-3 pt-4 text-[10.5px] font-bold uppercase tracking-wider text-ink-500">
        <div class="px-2.5 py-1">Manage</div>
      </div>
      <a routerLink="/participants" routerLinkActive="bg-accent-soft text-accent-hover font-semibold"
         class="mx-2 my-px flex items-center gap-2.5 rounded-md px-3 py-2 text-[13.5px]
                text-ink-700 transition hover:bg-surface-hover">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
          <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
        </svg>
        Participants
      </a>
      <div class="mx-2 my-px flex cursor-not-allowed items-center gap-2.5 rounded-md px-3 py-2 text-[13.5px] text-ink-400">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        Plans & Goals
        <span class="ml-auto text-[10px] font-semibold uppercase tracking-wider">Soon</span>
      </div>
      <div class="mx-2 my-px flex cursor-not-allowed items-center gap-2.5 rounded-md px-3 py-2 text-[13.5px] text-ink-400">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
          <circle cx="12" cy="7" r="4"/>
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        </svg>
        Staff
        <span class="ml-auto text-[10px] font-semibold uppercase tracking-wider">Soon</span>
      </div>
      <div class="mx-2 my-px flex cursor-not-allowed items-center gap-2.5 rounded-md px-3 py-2 text-[13.5px] text-ink-400">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
          <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
        </svg>
        Knowledge base
        <span class="ml-auto text-[10px] font-semibold uppercase tracking-wider">Soon</span>
      </div>

      <div class="mt-auto"></div>

      <div class="flex items-center gap-2.5 border-t border-ink-200 px-3.5 py-3">
        <div class="flex h-8 w-8 items-center justify-center rounded-full bg-accent
                    text-[12px] font-bold text-white">
          {{ user()?.initials || 'U' }}
        </div>
        <div class="min-w-0 flex-1">
          <div class="truncate text-[13px] font-semibold">{{ user()?.name || 'Guest' }}</div>
          <div class="text-[11px] text-ink-500">{{ user()?.roleLabel || '' }}</div>
        </div>
        <button
          (click)="onLogout()"
          aria-label="Sign out"
          title="Sign out"
          class="flex h-7 w-7 items-center justify-center rounded text-ink-500
                 transition hover:bg-surface-hover hover:text-ink-900"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </button>
      </div>
    </aside>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppSidebarComponent {
  private auth = inject(AuthStore);
  protected layout = inject(LayoutStore);
  readonly user = this.auth.currentUser;

  async onLogout() {
    await this.auth.signOut();
    window.location.href = '/login';
  }
}

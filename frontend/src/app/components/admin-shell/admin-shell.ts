import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { AppSidebarComponent } from '../app-sidebar/app-sidebar';
import { LayoutStore } from '../../services/layout.store';

@Component({
  selector: 'app-admin-shell',
  standalone: true,
  imports: [AppSidebarComponent, RouterOutlet],
  template: `
    <div class="flex h-screen w-screen overflow-hidden">
      <app-sidebar></app-sidebar>
      <div class="flex min-w-0 flex-1 flex-col">
        <!-- Mobile top bar — the only way to reach the nav drawer below md -->
        <header class="flex items-center gap-2.5 border-b border-ink-200 bg-surface px-4 py-2.5 md:hidden">
          <button
            type="button"
            (click)="layout.toggleNav()"
            aria-label="Open menu"
            class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md
                   text-ink-700 transition hover:bg-surface-hover"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" class="h-5 w-5">
              <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          <img src="favicon.png" alt="" class="h-7 w-7 flex-shrink-0 object-contain" />
          <span class="truncate font-display text-[14px] font-semibold tracking-tight text-brand-green">
            Special Care Australia
          </span>
        </header>
        <div class="flex min-h-0 flex-1 flex-col">
          <router-outlet></router-outlet>
        </div>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminShellComponent {
  protected layout = inject(LayoutStore);
}

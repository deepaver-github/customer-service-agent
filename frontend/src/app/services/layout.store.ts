import { Injectable, inject, signal } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs/operators';

/**
 * Cross-component UI state for the responsive shell.
 * `navOpen` drives the mobile off-canvas navigation drawer (app-sidebar);
 * it's irrelevant at >=md where the sidebar is statically docked.
 */
@Injectable({ providedIn: 'root' })
export class LayoutStore {
  private router = inject(Router);

  readonly navOpen = signal(false);

  constructor() {
    // Close the drawer whenever a navigation completes so it never lingers
    // over the newly-routed page on mobile.
    this.router.events
      .pipe(filter((e) => e instanceof NavigationEnd))
      .subscribe(() => this.closeNav());
  }

  openNav(): void {
    this.navOpen.set(true);
  }

  closeNav(): void {
    this.navOpen.set(false);
  }

  toggleNav(): void {
    this.navOpen.update((v) => !v);
  }
}

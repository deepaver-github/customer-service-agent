import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { AppSidebarComponent } from '../app-sidebar/app-sidebar';

@Component({
  selector: 'app-admin-shell',
  standalone: true,
  imports: [AppSidebarComponent, RouterOutlet],
  template: `
    <div class="flex h-screen w-screen overflow-hidden">
      <app-sidebar></app-sidebar>
      <router-outlet></router-outlet>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminShellComponent {}

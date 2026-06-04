import { Routes } from '@angular/router';
import { authGuard, loginGuard } from './services/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    canActivate: [loginGuard],
    loadComponent: () =>
      import('./components/login/login').then((m) => m.LoginComponent),
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./components/admin-shell/admin-shell').then((m) => m.AdminShellComponent),
    children: [
      {
        path: '',
        pathMatch: 'full',
        loadComponent: () =>
          import('./components/dashboard/dashboard').then((m) => m.DashboardComponent),
      },
      {
        path: 'chat',
        loadComponent: () =>
          import('./components/chat-page/chat-page').then((m) => m.ChatPageComponent),
      },
      {
        path: 'participants',
        loadComponent: () =>
          import('./components/participant-list/participant-list').then(
            (m) => m.ParticipantListComponent,
          ),
      },
      {
        path: 'participants/new',
        loadComponent: () =>
          import('./components/participant-new/participant-new').then(
            (m) => m.ParticipantNewComponent,
          ),
      },
      {
        path: 'participants/:id/edit',
        loadComponent: () =>
          import('./components/participant-edit/participant-edit').then(
            (m) => m.ParticipantEditComponent,
          ),
      },
      {
        path: 'participants/:id',
        loadComponent: () =>
          import('./components/participant-detail/participant-detail').then(
            (m) => m.ParticipantDetailComponent,
          ),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];

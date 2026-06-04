import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthStore, UserRole } from '../../services/auth.store';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="relative flex h-screen w-screen items-center justify-center overflow-hidden bg-surface px-4 sm:px-6">
      <div class="pointer-events-none absolute inset-0">
        <div class="absolute -top-32 -left-40 h-[480px] w-[760px] rounded-full
                    bg-brand-teal/30 blur-3xl"></div>
        <div class="absolute -bottom-32 -right-40 h-[420px] w-[680px] rounded-full
                    bg-brand-green/15 blur-3xl"></div>
      </div>

      <div class="relative w-full max-w-[420px] rounded-2xl bg-white p-7 sm:p-10
                  shadow-[0_24px_80px_rgba(24,24,27,0.12)]">
        <img src="favicon.png" alt="Special Care Australia"
             class="mx-auto mb-5 h-14 w-14 object-contain" />
        <h1 class="text-center font-display text-[22px] font-semibold tracking-tight">
          Special Care Australia
        </h1>
        <p class="mb-6 text-center text-[13.5px] text-ink-500">
          Sign in to the Care Assistant
        </p>

        <div class="mb-5 flex rounded-lg bg-ink-100 p-1">
          <button
            type="button"
            class="flex-1 rounded-md py-2 text-[13px] font-semibold transition"
            [class.bg-white]="role() === 'staff'"
            [class.text-accent-hover]="role() === 'staff'"
            [class.shadow-soft]="role() === 'staff'"
            [class.text-ink-500]="role() !== 'staff'"
            (click)="role.set('staff')"
          >
            I'm a team member
          </button>
          <button
            type="button"
            class="flex-1 rounded-md py-2 text-[13px] font-semibold transition"
            [class.bg-white]="role() === 'participant'"
            [class.text-accent-hover]="role() === 'participant'"
            [class.shadow-soft]="role() === 'participant'"
            [class.text-ink-500]="role() !== 'participant'"
            (click)="role.set('participant')"
          >
            Participant / family
          </button>
        </div>

        <form (submit)="onSubmit($event)">
          <label class="mb-3 block">
            <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">
              {{ role() === 'staff' ? 'Work email' : 'Email' }}
            </span>
            <input
              type="email"
              required
              autocomplete="email"
              [(ngModel)]="email"
              name="email"
              [placeholder]="role() === 'staff' ? 'maria.lo@specialcareaust.example' : 'you@example.com'"
              class="w-full rounded-lg border border-ink-200 px-3 py-2.5 text-[14px]
                     outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft"
            />
          </label>
          <label class="mb-2 block">
            <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">Password</span>
            <input
              type="password"
              required
              autocomplete="current-password"
              [(ngModel)]="password"
              name="password"
              placeholder="••••••••"
              class="w-full rounded-lg border border-ink-200 px-3 py-2.5 text-[14px]
                     outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft"
            />
          </label>
          <div class="mb-5 mt-2 flex items-center justify-between text-[12.5px]">
            <label class="flex items-center gap-1.5 text-ink-700">
              <input type="checkbox" [(ngModel)]="stayLoggedIn" name="stayLoggedIn" />
              Stay signed in for 30 days
            </label>
            <a href="#" class="font-semibold text-accent-hover hover:underline">Forgot password?</a>
          </div>
          @if (errorMsg()) {
            <div class="mb-3 rounded-md border border-escalation-text/30 bg-escalation-bg px-3 py-2 text-[12.5px] text-escalation-text">
              {{ errorMsg() }}
            </div>
          }
          <button
            type="submit"
            class="w-full rounded-lg bg-accent px-3 py-3 text-[14.5px] font-semibold text-white
                   shadow-send transition hover:bg-accent-hover disabled:opacity-60"
            [disabled]="!canSubmit() || submitting()"
          >
            {{ submitting() ? 'Signing in…' : 'Sign in' }}
          </button>
        </form>

        <p class="mt-5 text-center text-[12px] text-ink-500">
          Trouble signing in? Contact
          <a href="#" class="font-semibold text-accent-hover hover:underline">your manager</a>
          or call (02) 9000 0000.
        </p>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LoginComponent {
  private auth = inject(AuthStore);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  email = '';
  password = '';
  stayLoggedIn = true;
  readonly role = signal<UserRole>('staff');
  readonly submitting = signal(false);
  readonly errorMsg = signal<string | null>(
    this.route.snapshot.queryParamMap.get('reason') === 'expired'
      ? 'Your session expired — please sign in again.'
      : null,
  );

  canSubmit(): boolean {
    return this.email.trim().length > 0 && this.password.length > 0;
  }

  async onSubmit(event: Event) {
    event.preventDefault();
    if (!this.canSubmit() || this.submitting()) return;
    this.submitting.set(true);
    this.errorMsg.set(null);
    try {
      await this.auth.signIn(this.email.trim(), this.password);
      this.router.navigate(['/']);
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 401) {
        this.errorMsg.set("That email and password don't match. Try again.");
      } else if (status === 400) {
        this.errorMsg.set('Please enter both your email and password.');
      } else {
        this.errorMsg.set("Couldn't reach the server. Check your connection and retry.");
      }
    } finally {
      this.submitting.set(false);
    }
  }
}

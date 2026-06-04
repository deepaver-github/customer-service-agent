import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ParticipantCreatePayload } from '../../models/participant.model';
import { ParticipantService } from '../../services/participant.service';

const DISABILITY_CATEGORIES = [
  'intellectual',
  'autism',
  'psychosocial',
  'physical',
  'sensory',
  'neurological',
  'acquired_brain_injury',
  'other',
] as const;

const STATES = ['ACT', 'NSW', 'NT', 'QLD', 'SA', 'TAS', 'VIC', 'WA'] as const;

const STATUSES = ['onboarding', 'active', 'paused', 'exited'] as const;

@Component({
  selector: 'app-participant-new',
  standalone: true,
  imports: [FormsModule, RouterLink],
  template: `
    <div class="flex h-full min-w-0 flex-1 flex-col bg-surface">
      <header class="flex items-center gap-3.5 border-b border-ink-200 bg-surface/85 px-7 py-3.5">
        <a routerLink="/participants" class="text-[13.5px] text-ink-500 hover:underline">Participants</a>
        <span class="text-ink-400">›</span>
        <span class="flex-1 font-display text-[15px] font-semibold tracking-tight">New participant</span>
      </header>

      <div class="scroll-polish flex-1 overflow-y-auto px-8 pb-12 pt-7">
        <form (submit)="onSubmit($event)" class="mx-auto max-w-[760px]">
          <p class="mb-6 text-[13.5px] text-ink-500">
            Create a new participant record. NDIS number, name, and status are required; everything else can be filled in later.
          </p>

          @if (errorMsg()) {
            <div class="mb-4 rounded-md border border-escalation-text/30 bg-escalation-bg px-4 py-3 text-[13px] text-escalation-text">
              {{ errorMsg() }}
            </div>
          }

          <!-- Identity -->
          <section class="mb-6 rounded-xl border border-ink-200 bg-white p-5">
            <h3 class="mb-4 font-display text-[14px] font-bold uppercase tracking-wider text-ink-700">Identity</h3>
            <div class="grid grid-cols-2 gap-4">
              <label class="block">
                <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">NDIS number *</span>
                <input type="text" required [(ngModel)]="form.ndis_number" name="ndis_number"
                       placeholder="430123456" autocomplete="off"
                       class="w-full rounded-md border border-ink-200 px-3 py-2 text-[13.5px]
                              outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft" />
              </label>
              <label class="block">
                <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">Status *</span>
                <select [(ngModel)]="form.status" name="status"
                        class="w-full rounded-md border border-ink-200 bg-white px-3 py-2 text-[13.5px]
                               outline-none focus:border-accent focus:ring-2 focus:ring-accent-soft">
                  @for (s of statuses; track s) {
                    <option [value]="s">{{ s }}</option>
                  }
                </select>
              </label>
              <label class="block">
                <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">First name *</span>
                <input type="text" required [(ngModel)]="form.first_name" name="first_name"
                       class="w-full rounded-md border border-ink-200 px-3 py-2 text-[13.5px]
                              outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft" />
              </label>
              <label class="block">
                <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">Last name *</span>
                <input type="text" required [(ngModel)]="form.last_name" name="last_name"
                       class="w-full rounded-md border border-ink-200 px-3 py-2 text-[13.5px]
                              outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft" />
              </label>
              <label class="block">
                <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">Preferred name</span>
                <input type="text" [(ngModel)]="form.preferred_name" name="preferred_name"
                       class="w-full rounded-md border border-ink-200 px-3 py-2 text-[13.5px]
                              outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft" />
              </label>
              <label class="block">
                <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">Date of birth</span>
                <input type="date" [(ngModel)]="form.dob" name="dob"
                       class="w-full rounded-md border border-ink-200 px-3 py-2 text-[13.5px]
                              outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft" />
              </label>
              <label class="block col-span-2">
                <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">Primary disability category</span>
                <select [(ngModel)]="form.primary_disability_category" name="primary_disability_category"
                        class="w-full rounded-md border border-ink-200 bg-white px-3 py-2 text-[13.5px]
                               outline-none focus:border-accent focus:ring-2 focus:ring-accent-soft">
                  <option [ngValue]="null">—</option>
                  @for (c of categories; track c) {
                    <option [value]="c">{{ c.replace('_', ' ') }}</option>
                  }
                </select>
              </label>
              <label class="block col-span-2">
                <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">Communication needs</span>
                <textarea rows="2" [(ngModel)]="form.communication_needs" name="communication_needs"
                          placeholder="e.g. Prefers SMS over phone. Allow extra time for spoken responses."
                          class="w-full rounded-md border border-ink-200 px-3 py-2 text-[13.5px]
                                 outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft"></textarea>
              </label>
            </div>
          </section>

          <!-- Contact -->
          <section class="mb-6 rounded-xl border border-ink-200 bg-white p-5">
            <h3 class="mb-4 font-display text-[14px] font-bold uppercase tracking-wider text-ink-700">Contact</h3>
            <div class="grid grid-cols-2 gap-4">
              <label class="block">
                <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">Phone</span>
                <input type="tel" [(ngModel)]="form.phone" name="phone" placeholder="+61 4 …"
                       class="w-full rounded-md border border-ink-200 px-3 py-2 text-[13.5px]
                              outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft" />
              </label>
              <label class="block">
                <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">Email</span>
                <input type="email" [(ngModel)]="form.email" name="email" placeholder="name@example.com"
                       class="w-full rounded-md border border-ink-200 px-3 py-2 text-[13.5px]
                              outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft" />
              </label>
              <label class="block col-span-2">
                <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">Street address</span>
                <input type="text" [(ngModel)]="form.address_line1" name="address_line1"
                       placeholder="14 Acacia Street"
                       class="w-full rounded-md border border-ink-200 px-3 py-2 text-[13.5px]
                              outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft" />
              </label>
              <label class="block">
                <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">Suburb</span>
                <input type="text" [(ngModel)]="form.suburb" name="suburb"
                       class="w-full rounded-md border border-ink-200 px-3 py-2 text-[13.5px]
                              outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft" />
              </label>
              <div class="grid grid-cols-2 gap-3">
                <label class="block">
                  <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">State</span>
                  <select [(ngModel)]="form.state" name="state"
                          class="w-full rounded-md border border-ink-200 bg-white px-3 py-2 text-[13.5px]
                                 outline-none focus:border-accent focus:ring-2 focus:ring-accent-soft">
                    <option [ngValue]="null">—</option>
                    @for (s of states; track s) {
                      <option [value]="s">{{ s }}</option>
                    }
                  </select>
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">Postcode</span>
                  <input type="text" [(ngModel)]="form.postcode" name="postcode" maxlength="4"
                         class="w-full rounded-md border border-ink-200 px-3 py-2 text-[13.5px]
                                outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft" />
                </label>
              </div>
            </div>
          </section>

          <div class="flex items-center gap-3">
            <button type="submit" [disabled]="!canSubmit() || submitting()"
                    class="rounded-md bg-accent px-4 py-2 text-[13.5px] font-semibold text-white
                           shadow-send transition hover:bg-accent-hover disabled:opacity-60">
              {{ submitting() ? 'Creating…' : 'Create participant' }}
            </button>
            <a routerLink="/participants"
               class="text-[13.5px] font-semibold text-ink-500 hover:text-ink-900">Cancel</a>
          </div>
        </form>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ParticipantNewComponent {
  private participants = inject(ParticipantService);
  private router = inject(Router);

  readonly categories = DISABILITY_CATEGORIES;
  readonly states = STATES;
  readonly statuses = STATUSES;
  readonly submitting = signal(false);
  readonly errorMsg = signal<string | null>(null);

  form: ParticipantCreatePayload = {
    ndis_number: '',
    first_name: '',
    last_name: '',
    preferred_name: null,
    dob: null,
    primary_disability_category: null,
    communication_needs: null,
    address_line1: null,
    suburb: null,
    state: null,
    postcode: null,
    phone: null,
    email: null,
    status: 'onboarding',
  };

  canSubmit(): boolean {
    return (
      this.form.ndis_number.trim().length > 0 &&
      this.form.first_name.trim().length > 0 &&
      this.form.last_name.trim().length > 0
    );
  }

  async onSubmit(event: Event) {
    event.preventDefault();
    if (!this.canSubmit() || this.submitting()) return;
    this.submitting.set(true);
    this.errorMsg.set(null);

    // Coerce empty strings to null so backend Pydantic validation doesn't choke.
    const bag: Record<string, unknown> = { ...this.form };
    for (const k of Object.keys(bag)) {
      const v = bag[k];
      if (typeof v === 'string' && v.trim() === '') {
        bag[k] = null;
      }
    }
    const payload = bag as unknown as ParticipantCreatePayload;
    payload.ndis_number = this.form.ndis_number.trim();
    payload.first_name = this.form.first_name.trim();
    payload.last_name = this.form.last_name.trim();

    try {
      const created = await this.participants.create(payload);
      this.router.navigate(['/participants', created.id]);
    } catch (err: unknown) {
      const e = err as { status?: number; error?: { detail?: string } };
      if (e.status === 409) {
        this.errorMsg.set(e.error?.detail || 'That NDIS number is already in use.');
      } else if (e.status === 400 && e.error?.detail) {
        this.errorMsg.set(e.error.detail);
      } else if (e.status === 401 || e.status === 403) {
        this.errorMsg.set("You don't have permission to create participants.");
      } else {
        this.errorMsg.set("Couldn't create participant — check your connection and try again.");
      }
    } finally {
      this.submitting.set(false);
    }
  }
}

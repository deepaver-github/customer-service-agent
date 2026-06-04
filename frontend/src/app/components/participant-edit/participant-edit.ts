import { ChangeDetectionStrategy, Component, OnInit, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ParticipantUpdatePayload } from '../../models/participant.model';
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

interface EditForm {
  ndis_number: string;
  first_name: string;
  last_name: string;
  preferred_name: string;
  dob: string;
  primary_disability_category: string;
  communication_needs: string;
  address_line1: string;
  address_line2: string;
  suburb: string;
  state: string;
  postcode: string;
  phone: string;
  email: string;
  status: string;
}

const EMPTY_FORM: EditForm = {
  ndis_number: '',
  first_name: '',
  last_name: '',
  preferred_name: '',
  dob: '',
  primary_disability_category: '',
  communication_needs: '',
  address_line1: '',
  address_line2: '',
  suburb: '',
  state: '',
  postcode: '',
  phone: '',
  email: '',
  status: 'onboarding',
};

@Component({
  selector: 'app-participant-edit',
  standalone: true,
  imports: [FormsModule, RouterLink],
  template: `
    <div class="flex h-full min-w-0 flex-1 flex-col bg-surface">
      <header class="flex items-center gap-3 border-b border-ink-200 bg-surface/85 px-4 py-3 sm:gap-3.5 sm:px-7 sm:py-3.5">
        <a routerLink="/participants" class="flex-shrink-0 text-[13.5px] text-ink-500 hover:underline">Participants</a>
        <span class="text-ink-400">›</span>
        <a [routerLink]="['/participants', id()]" class="hidden flex-shrink-0 text-[13.5px] text-ink-500 hover:underline sm:inline">
          @if (displayName()) { {{ displayName() }} } @else { Participant }
        </a>
        <span class="hidden text-ink-400 sm:inline">›</span>
        <span class="flex-1 font-display text-[15px] font-semibold tracking-tight">Edit profile</span>
      </header>

      <div class="scroll-polish flex-1 overflow-y-auto px-4 pb-12 pt-7 sm:px-6 md:px-8">
        @if (loading()) {
          <div class="py-10 text-center text-[13px] text-ink-500">Loading…</div>
        } @else if (loadError()) {
          <div class="mx-auto max-w-[760px] rounded-md border border-escalation-text/30 bg-escalation-bg px-4 py-3 text-[13px] text-escalation-text">
            {{ loadError() }}
          </div>
        } @else {
          <form (submit)="onSubmit($event)" class="mx-auto max-w-[760px]">
            <p class="mb-6 text-[13.5px] text-ink-500">
              Update the participant's profile. Leave a field unchanged to keep its current value.
            </p>

            @if (errorMsg()) {
              <div class="mb-4 rounded-md border border-escalation-text/30 bg-escalation-bg px-4 py-3 text-[13px] text-escalation-text">
                {{ errorMsg() }}
              </div>
            }

            <!-- Identity -->
            <section class="mb-6 rounded-xl border border-ink-200 bg-white p-5">
              <h3 class="mb-4 font-display text-[14px] font-bold uppercase tracking-wider text-ink-700">Identity</h3>
              <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <label class="block">
                  <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">NDIS number *</span>
                  <input type="text" required [(ngModel)]="form.ndis_number" name="ndis_number"
                         autocomplete="off"
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
                <label class="block sm:col-span-2">
                  <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">Primary disability category</span>
                  <select [(ngModel)]="form.primary_disability_category" name="primary_disability_category"
                          class="w-full rounded-md border border-ink-200 bg-white px-3 py-2 text-[13.5px]
                                 outline-none focus:border-accent focus:ring-2 focus:ring-accent-soft">
                    <option value="">—</option>
                    @for (c of categories; track c) {
                      <option [value]="c">{{ c.replace('_', ' ') }}</option>
                    }
                  </select>
                </label>
                <label class="block sm:col-span-2">
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
              <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
                <label class="block sm:col-span-2">
                  <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">Street address</span>
                  <input type="text" [(ngModel)]="form.address_line1" name="address_line1"
                         class="w-full rounded-md border border-ink-200 px-3 py-2 text-[13.5px]
                                outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft" />
                </label>
                <label class="block sm:col-span-2">
                  <span class="mb-1.5 block text-[12px] font-semibold text-ink-700">Address line 2</span>
                  <input type="text" [(ngModel)]="form.address_line2" name="address_line2"
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
                      <option value="">—</option>
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
                {{ submitting() ? 'Saving…' : 'Save changes' }}
              </button>
              <a [routerLink]="['/participants', id()]"
                 class="text-[13.5px] font-semibold text-ink-500 hover:text-ink-900">Cancel</a>
            </div>
          </form>
        }
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ParticipantEditComponent implements OnInit {
  private participants = inject(ParticipantService);
  private router = inject(Router);

  readonly id = input.required<string>();
  readonly categories = DISABILITY_CATEGORIES;
  readonly states = STATES;
  readonly statuses = STATUSES;

  readonly loading = signal(true);
  readonly loadError = signal<string | null>(null);
  readonly submitting = signal(false);
  readonly errorMsg = signal<string | null>(null);
  readonly displayName = signal<string>('');

  form: EditForm = { ...EMPTY_FORM };

  async ngOnInit() {
    this.loading.set(true);
    try {
      const p = await this.participants.get(this.id());
      this.form = {
        ndis_number: p.ndis_number ?? '',
        first_name: p.first_name ?? '',
        last_name: p.last_name ?? '',
        preferred_name: p.preferred_name ?? '',
        dob: p.dob ?? '',
        primary_disability_category: p.primary_disability_category ?? '',
        communication_needs: p.communication_needs ?? '',
        address_line1: p.address_line1 ?? '',
        address_line2: p.address_line2 ?? '',
        suburb: p.suburb ?? '',
        state: p.state ?? '',
        postcode: p.postcode ?? '',
        phone: p.phone ?? '',
        email: p.email ?? '',
        status: p.status ?? 'onboarding',
      };
      this.displayName.set(`${p.preferred_name || p.first_name} ${p.last_name}`.trim());
    } catch (err: unknown) {
      const e = err as { status?: number };
      if (e.status === 403) {
        this.loadError.set("You don't have permission to view this participant.");
      } else if (e.status === 404) {
        this.loadError.set('Participant not found.');
      } else {
        this.loadError.set("Couldn't load this participant — check your connection and try again.");
      }
    } finally {
      this.loading.set(false);
    }
  }

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

    const payload: ParticipantUpdatePayload = {
      ndis_number: this.form.ndis_number.trim(),
      first_name: this.form.first_name.trim(),
      last_name: this.form.last_name.trim(),
      preferred_name: this.form.preferred_name.trim() || null,
      dob: this.form.dob || null,
      primary_disability_category: this.form.primary_disability_category || null,
      communication_needs: this.form.communication_needs.trim() || null,
      address_line1: this.form.address_line1.trim() || null,
      address_line2: this.form.address_line2.trim() || null,
      suburb: this.form.suburb.trim() || null,
      state: this.form.state || null,
      postcode: this.form.postcode.trim() || null,
      phone: this.form.phone.trim() || null,
      email: this.form.email.trim() || null,
      status: this.form.status,
    };

    try {
      const updated = await this.participants.update(this.id(), payload);
      this.router.navigate(['/participants', updated.id]);
    } catch (err: unknown) {
      const e = err as { status?: number; error?: { detail?: string } };
      if (e.status === 409) {
        this.errorMsg.set(e.error?.detail || 'That NDIS number is already in use.');
      } else if (e.status === 400 && e.error?.detail) {
        this.errorMsg.set(e.error.detail);
      } else if (e.status === 401 || e.status === 403) {
        this.errorMsg.set("You don't have permission to edit this participant.");
      } else if (e.status === 404) {
        this.errorMsg.set('Participant not found.');
      } else {
        this.errorMsg.set("Couldn't save changes — check your connection and try again.");
      }
    } finally {
      this.submitting.set(false);
    }
  }
}

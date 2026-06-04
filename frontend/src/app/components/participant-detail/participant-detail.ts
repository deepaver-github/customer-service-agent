import { ChangeDetectionStrategy, Component, OnInit, computed, inject, input, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { ParticipantDetail } from '../../models/participant.model';
import { ParticipantService } from '../../services/participant.service';

type Tab = 'overview' | 'contacts' | 'plan' | 'services' | 'clinical' | 'history';

@Component({
  selector: 'app-participant-detail',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="flex h-full min-w-0 flex-1 flex-col bg-surface">
      <header class="flex items-center gap-3.5 border-b border-ink-200 bg-surface/85 px-7 py-3.5">
        <a routerLink="/participants" class="text-[13.5px] text-ink-500 hover:underline">Participants</a>
        <span class="text-ink-400">›</span>
        <span class="flex-1 font-display text-[15px] font-semibold tracking-tight">
          @if (data(); as p) {
            {{ p.preferred_name || p.first_name }} {{ p.last_name }}
          } @else {
            Loading…
          }
        </span>
        <a [routerLink]="['/participants', id(), 'edit']"
           class="rounded-md border border-ink-200 bg-white px-3 py-1.5 text-[13px] font-semibold text-ink-700
                  transition hover:bg-surface-hover">
          Edit profile
        </a>
      </header>

      <div class="scroll-polish flex-1 overflow-y-auto px-8 pb-12 pt-6">
        @if (data(); as p) {
          <!-- Header -->
          <div class="mb-5 flex items-start gap-4 border-b border-ink-200 pb-5">
            <div class="flex h-14 w-14 items-center justify-center rounded-full bg-accent-soft
                        font-display text-[18px] font-bold text-accent-hover">
              {{ initials(p) }}
            </div>
            <div class="min-w-0 flex-1">
              <h2 class="font-display text-[22px] font-semibold tracking-tight">
                {{ p.preferred_name || p.first_name }} {{ p.last_name }}
              </h2>
              <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-ink-500">
                <span class="font-mono text-[12.5px]">NDIS {{ p.ndis_number }}</span>
                @if (p.primary_disability_category) {
                  <span>·</span>
                  <span class="capitalize">{{ p.primary_disability_category.replace('_', ' ') }}</span>
                }
                @if (p.suburb) {
                  <span>·</span>
                  <span>{{ p.suburb }} {{ p.state }}</span>
                }
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
              </div>
            </div>
          </div>

          <!-- Tabs -->
          <div class="mb-6 flex gap-1 border-b border-ink-200">
            @for (t of tabList(); track t.key) {
              <button
                type="button"
                (click)="tab.set(t.key)"
                class="border-b-2 px-4 py-3 text-[13.5px] transition"
                [class.border-accent]="tab() === t.key"
                [class.text-accent-hover]="tab() === t.key"
                [class.font-semibold]="tab() === t.key"
                [class.border-transparent]="tab() !== t.key"
                [class.text-ink-500]="tab() !== t.key"
                [class.hover:text-ink-900]="tab() !== t.key"
              >
                {{ t.label }}
                @if (t.count !== undefined) {
                  <span class="ml-1.5 rounded-full px-1.5 py-0.5 text-[10.5px] font-semibold"
                        [class.bg-accent-soft]="tab() === t.key"
                        [class.text-accent-hover]="tab() === t.key"
                        [class.bg-ink-100]="tab() !== t.key"
                        [class.text-ink-700]="tab() !== t.key">
                    {{ t.count }}
                  </span>
                }
              </button>
            }
          </div>

          <!-- OVERVIEW -->
          @if (tab() === 'overview') {
            <div class="grid grid-cols-2 gap-4">
              <div class="rounded-xl border border-ink-200 bg-white p-5">
                <h4 class="mb-3 font-display text-[12px] font-bold uppercase tracking-wider text-ink-700">Profile</h4>
                <dl class="grid grid-cols-[140px_1fr] gap-y-2 text-[13.5px]">
                  <dt class="text-ink-500">Preferred name</dt><dd>{{ p.preferred_name || '—' }}</dd>
                  <dt class="text-ink-500">Date of birth</dt><dd>{{ formatDate(p.dob) || '—' }}</dd>
                  <dt class="text-ink-500">Primary disability</dt><dd class="capitalize">{{ (p.primary_disability_category || '—').replace('_', ' ') }}</dd>
                  <dt class="text-ink-500">Phone</dt><dd>{{ p.phone || '—' }}</dd>
                  <dt class="text-ink-500">Email</dt><dd>{{ p.email || '—' }}</dd>
                  <dt class="text-ink-500">Address</dt>
                  <dd>
                    @if (p.address_line1) {
                      {{ p.address_line1 }}@if (p.address_line2) {, {{ p.address_line2 }}}
                      <br/>{{ p.suburb }} {{ p.state }} {{ p.postcode }}
                    } @else { — }
                  </dd>
                </dl>
              </div>

              <div class="rounded-xl border border-ink-200 bg-white p-5">
                <h4 class="mb-2 font-display text-[12px] font-bold uppercase tracking-wider text-ink-700">Communication needs</h4>
                <p class="mb-4 text-[13.5px] leading-relaxed">{{ p.communication_needs || '—' }}</p>
                <h4 class="mb-3 font-display text-[12px] font-bold uppercase tracking-wider text-ink-700">Assigned team</h4>
                @for (a of p.assigned_staff; track a.staff_id) {
                  <div class="mb-2 flex items-center gap-2.5 last:mb-0">
                    <div class="flex h-9 w-9 items-center justify-center rounded-full
                                bg-accent-soft text-[12px] font-bold text-accent-hover">
                      {{ a.staff_name.split(' ').map(n => n[0]).join('').slice(0, 2) }}
                    </div>
                    <div class="min-w-0 flex-1">
                      <div class="truncate text-[13.5px] font-semibold">{{ a.staff_name }}</div>
                      <div class="truncate text-[11.5px] text-ink-500 capitalize">
                        {{ a.staff_role.replace('_', ' ') }}
                      </div>
                    </div>
                    <span class="rounded-full bg-accent-soft px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-accent-hover">
                      {{ a.assignment_type }}
                    </span>
                  </div>
                } @empty {
                  <p class="text-[13px] text-ink-500">No team assigned yet.</p>
                }
              </div>

              <div class="col-span-2 flex items-center gap-3 rounded-xl border border-accent bg-gradient-to-r from-white to-accent-soft px-5 py-4">
                <img src="favicon.png" alt="" class="h-9 w-9 object-contain" />
                <div class="flex-1">
                  <div class="font-display text-[14px] font-semibold">Ask the Care Assistant about {{ p.first_name }}</div>
                  <p class="text-[12.5px] text-ink-700">
                    Quick lookups: "What are her current goals?" · "Who's her emergency contact?" · "When does her plan end?"
                  </p>
                </div>
                <button (click)="openChat(p)"
                        class="rounded-md bg-accent px-3.5 py-2 text-[13px] font-semibold text-white
                               shadow-send transition hover:bg-accent-hover">
                  Open chat ↗
                </button>
              </div>
            </div>
          }

          <!-- CONTACTS -->
          @if (tab() === 'contacts') {
            <div class="grid grid-cols-2 gap-4">
              @for (c of p.contacts; track c.id) {
                <div class="rounded-xl border border-ink-200 bg-white p-5">
                  <div class="mb-3 flex items-center gap-2.5">
                    <div class="flex h-9 w-9 items-center justify-center rounded-full bg-accent-soft
                                font-display text-[12px] font-bold text-accent-hover">
                      {{ initialsFromName(c.name) }}
                    </div>
                    <div class="min-w-0 flex-1">
                      <div class="truncate text-[14px] font-semibold">{{ c.name }}</div>
                      <div class="truncate text-[11.5px] uppercase tracking-wider text-ink-500">
                        {{ c.relationship.replace('_', ' ') }}
                      </div>
                    </div>
                  </div>
                  <dl class="grid grid-cols-[55px_1fr] gap-y-1.5 text-[13px]">
                    <dt class="text-ink-500">Phone</dt><dd>{{ c.phone || '—' }}</dd>
                    <dt class="text-ink-500">Email</dt><dd>{{ c.email || '—' }}</dd>
                    @if (c.notes) {
                      <dt class="text-ink-500">Notes</dt><dd>{{ c.notes }}</dd>
                    }
                  </dl>
                  @if (c.is_primary || c.is_emergency) {
                    <div class="mt-3 flex gap-1.5">
                      @if (c.is_primary) {
                        <span class="rounded-full bg-accent-soft px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-accent-hover">Primary</span>
                      }
                      @if (c.is_emergency) {
                        <span class="rounded-full bg-escalation-bg px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-escalation-text">Emergency</span>
                      }
                    </div>
                  }
                </div>
              } @empty {
                <div class="col-span-2 rounded-xl border border-dashed border-ink-200 px-5 py-10 text-center text-[13px] text-ink-500">
                  No contacts on file.
                </div>
              }
            </div>
          }

          <!-- PLAN & GOALS -->
          @if (tab() === 'plan') {
            @if (p.active_plan; as plan) {
              <div class="mb-6 grid grid-cols-3 gap-6 rounded-xl border border-accent/15
                          bg-gradient-to-br from-accent-soft to-brand-teal-soft p-6">
                <div>
                  <div class="text-[11px] font-bold uppercase tracking-wider text-accent-hover">Current plan</div>
                  <div class="mt-1 font-display text-[20px] font-semibold">{{ plan.plan_number }}</div>
                  <div class="text-[13px] text-ink-700">
                    {{ formatDate(plan.start_date) }} → {{ formatDate(plan.end_date) }} · {{ plan.management_type.replace('_', '-') }}
                  </div>
                </div>
                <div>
                  <div class="text-[11px] font-bold uppercase tracking-wider text-accent-hover">Plan manager</div>
                  <div class="mt-1 font-display text-[15px] font-semibold">
                    {{ plan.plan_manager_name || '—' }}
                  </div>
                  <div class="text-[13px] text-ink-700">{{ plan.plan_manager_contact || '' }}</div>
                </div>
                <div>
                  <div class="text-[11px] font-bold uppercase tracking-wider text-accent-hover">Active goals</div>
                  <div class="mt-1 font-display text-[20px] font-semibold">{{ activeGoalCount() }}</div>
                  <div class="text-[13px] text-ink-700">{{ achievedGoalCount() }} achieved · {{ pausedGoalCount() }} paused</div>
                </div>
              </div>
            } @else {
              <div class="mb-6 rounded-xl border border-dashed border-ink-200 px-5 py-6 text-center text-[13px] text-ink-500">
                No active NDIS plan on file.
              </div>
            }

            <div class="mb-3 flex items-center">
              <h3 class="font-display text-[15px] font-semibold">Goals</h3>
              <button type="button" disabled title="Goal creation is coming soon"
                      class="ml-auto inline-flex cursor-not-allowed items-center gap-1.5 rounded-md
                             border border-dashed border-ink-200 bg-surface px-3 py-1.5
                             text-[12.5px] font-semibold text-ink-400">
                + Add goal
                <span class="rounded-full bg-ink-100 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider">Soon</span>
              </button>
            </div>
            <div class="grid grid-cols-2 gap-3">
              @for (g of p.goals; track g.id) {
                <div class="rounded-xl border border-ink-200 bg-white p-4">
                  <span class="mb-2 inline-block rounded bg-ink-100 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider text-ink-700">
                    {{ g.category }}
                  </span>
                  <p class="mb-2.5 text-[14px] leading-snug">{{ g.description }}</p>
                  <div class="flex items-center justify-between text-[12px] text-ink-500">
                    <span>
                      @if (g.target_date) { Target: {{ formatDate(g.target_date) }} }
                      @else { No target date }
                    </span>
                    <span class="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider"
                          [class.bg-accent-soft]="g.status === 'active'"
                          [class.text-accent-hover]="g.status === 'active'"
                          [class.bg-ink-100]="g.status !== 'active'"
                          [class.text-ink-700]="g.status !== 'active'">
                      {{ g.status }}
                    </span>
                  </div>
                </div>
              } @empty {
                <div class="col-span-2 rounded-xl border border-dashed border-ink-200 px-5 py-8 text-center text-[13px] text-ink-500">
                  No goals on file.
                </div>
              }
            </div>

            @if (p.service_agreements.length > 0) {
              <h3 class="mb-3 mt-7 font-display text-[15px] font-semibold">Service agreements</h3>
              <div class="overflow-hidden rounded-xl border border-ink-200 bg-white">
                <table class="w-full text-[13.5px]">
                  <thead>
                    <tr class="border-b border-ink-200 bg-ink-100 text-[11px] font-bold uppercase tracking-wider text-ink-500">
                      <th class="px-5 py-2.5 text-left">Service</th>
                      <th class="px-5 py-2.5 text-left">Period</th>
                      <th class="px-5 py-2.5 text-left">Scope</th>
                      <th class="px-5 py-2.5 text-left">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (a of p.service_agreements; track a.id) {
                      <tr class="border-b border-ink-100 last:border-b-0">
                        <td class="px-5 py-3">
                          <div class="font-semibold">{{ a.service_name }}</div>
                          <div class="text-[11.5px] text-ink-500">{{ a.service_code }}</div>
                        </td>
                        <td class="px-5 py-3 text-[13px]">
                          {{ formatDate(a.valid_from) }} → {{ a.valid_to ? formatDate(a.valid_to) : 'open-ended' }}
                        </td>
                        <td class="px-5 py-3 text-[13px]">{{ a.scope_notes || '—' }}</td>
                        <td class="px-5 py-3">
                          <span class="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider"
                                [class.bg-accent-soft]="a.status === 'active'"
                                [class.text-accent-hover]="a.status === 'active'"
                                [class.bg-ink-100]="a.status !== 'active'"
                                [class.text-ink-700]="a.status !== 'active'">
                            {{ a.status }}
                          </span>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            }
          }

          <!-- SERVICES — upcoming + recent shifts -->
          @if (tab() === 'services') {
            <h3 class="mb-3 font-display text-[15px] font-semibold">Upcoming shifts</h3>
            @if (p.upcoming_shifts.length > 0) {
              <div class="mb-6 overflow-hidden rounded-xl border border-ink-200 bg-white">
                <table class="w-full text-[13.5px]">
                  <thead>
                    <tr class="border-b border-ink-200 bg-ink-100 text-[11px] font-bold uppercase tracking-wider text-ink-500">
                      <th class="px-5 py-2.5 text-left">When</th>
                      <th class="px-5 py-2.5 text-left">Service</th>
                      <th class="px-5 py-2.5 text-left">Support worker</th>
                      <th class="px-5 py-2.5 text-left">Location</th>
                      <th class="px-5 py-2.5 text-left">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (s of p.upcoming_shifts; track s.id) {
                      <tr class="border-b border-ink-100 last:border-b-0">
                        <td class="px-5 py-3">
                          <div class="font-semibold">{{ formatDateTime(s.scheduled_start) }}</div>
                          <div class="text-[11.5px] text-ink-500">until {{ formatTime(s.scheduled_end) }}</div>
                        </td>
                        <td class="px-5 py-3 text-[13px]">{{ s.service_name }}</td>
                        <td class="px-5 py-3 text-[13px]">{{ s.support_worker_name || 'Unassigned' }}</td>
                        <td class="px-5 py-3 text-[13px]">{{ s.location || '—' }}</td>
                        <td class="px-5 py-3">
                          <span class="rounded-full bg-brand-teal-soft px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-brand-teal">
                            {{ s.status.replace('_', ' ') }}
                          </span>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            } @else {
              <div class="mb-6 rounded-xl border border-dashed border-ink-200 px-5 py-8 text-center text-[13px] text-ink-500">
                No scheduled shifts coming up.
              </div>
            }

            <h3 class="mb-3 font-display text-[15px] font-semibold">Recent shifts</h3>
            @if (p.recent_shifts.length > 0) {
              <div class="overflow-hidden rounded-xl border border-ink-200 bg-white">
                <table class="w-full text-[13.5px]">
                  <thead>
                    <tr class="border-b border-ink-200 bg-ink-100 text-[11px] font-bold uppercase tracking-wider text-ink-500">
                      <th class="px-5 py-2.5 text-left">When</th>
                      <th class="px-5 py-2.5 text-left">Service</th>
                      <th class="px-5 py-2.5 text-left">Support worker</th>
                      <th class="px-5 py-2.5 text-left">Status</th>
                      <th class="px-5 py-2.5 text-left">Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (s of p.recent_shifts; track s.id) {
                      <tr class="border-b border-ink-100 last:border-b-0">
                        <td class="px-5 py-3">
                          <div class="font-semibold">{{ formatDateTime(s.scheduled_start) }}</div>
                        </td>
                        <td class="px-5 py-3 text-[13px]">{{ s.service_name }}</td>
                        <td class="px-5 py-3 text-[13px]">{{ s.support_worker_name || '—' }}</td>
                        <td class="px-5 py-3">
                          <span class="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider"
                                [class.bg-accent-soft]="s.status === 'completed'"
                                [class.text-accent-hover]="s.status === 'completed'"
                                [class.bg-ink-100]="s.status !== 'completed'"
                                [class.text-ink-700]="s.status !== 'completed'">
                            {{ s.status.replace('_', ' ') }}
                          </span>
                        </td>
                        <td class="px-5 py-3 text-[12.5px] text-ink-500">{{ s.cancelled_reason || '' }}</td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            } @else {
              <div class="rounded-xl border border-dashed border-ink-200 px-5 py-8 text-center text-[13px] text-ink-500">
                No past shifts on record.
              </div>
            }
          }

          <!-- CLINICAL — medications, preferences, risk, restrictive, open incidents -->
          @if (tab() === 'clinical') {
            <div class="grid grid-cols-2 gap-4">
              <!-- Medications -->
              <div class="col-span-2 overflow-hidden rounded-xl border border-ink-200 bg-white">
                <div class="flex items-center border-b border-ink-200 px-5 py-3">
                  <h3 class="font-display text-[14.5px] font-semibold">Active medications</h3>
                  <span class="ml-2 rounded-full bg-ink-100 px-2 py-0.5 text-[10.5px] font-semibold text-ink-700">
                    {{ p.medications.length }}
                  </span>
                </div>
                @if (p.medications.length > 0) {
                  <table class="w-full text-[13.5px]">
                    <thead>
                      <tr class="border-b border-ink-200 bg-ink-100 text-[11px] font-bold uppercase tracking-wider text-ink-500">
                        <th class="px-5 py-2.5 text-left">Medication</th>
                        <th class="px-5 py-2.5 text-left">Dose</th>
                        <th class="px-5 py-2.5 text-left">Frequency</th>
                        <th class="px-5 py-2.5 text-left">Route</th>
                        <th class="px-5 py-2.5 text-left">Prescriber</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (m of p.medications; track m.id) {
                        <tr class="border-b border-ink-100 last:border-b-0">
                          <td class="px-5 py-3">
                            <div class="font-semibold">{{ m.medication_name }}</div>
                            @if (m.prn) {
                              <span class="rounded bg-escalation-bg px-1.5 py-0.5 text-[10px] font-bold uppercase text-escalation-text">PRN</span>
                            }
                          </td>
                          <td class="px-5 py-3">{{ m.dose }}</td>
                          <td class="px-5 py-3 text-[13px]">{{ m.frequency }}</td>
                          <td class="px-5 py-3 capitalize">{{ m.route }}</td>
                          <td class="px-5 py-3 text-[12.5px] text-ink-500">{{ m.prescriber || '—' }}</td>
                        </tr>
                      }
                    </tbody>
                  </table>
                } @else {
                  <div class="px-5 py-6 text-center text-[13px] text-ink-500">No active medications.</div>
                }
              </div>

              <!-- Preferences -->
              <div class="overflow-hidden rounded-xl border border-ink-200 bg-white">
                <div class="flex items-center border-b border-ink-200 px-5 py-3">
                  <h3 class="font-display text-[14.5px] font-semibold">Preferences</h3>
                  <span class="ml-2 rounded-full bg-ink-100 px-2 py-0.5 text-[10.5px] font-semibold text-ink-700">
                    {{ p.preferences.length }}
                  </span>
                </div>
                @for (pref of p.preferences; track pref.id) {
                  <div class="border-b border-ink-100 px-5 py-3 last:border-b-0">
                    <div class="mb-1 flex items-center gap-2">
                      <span class="rounded bg-ink-100 px-1.5 py-0.5 text-[10.5px] font-bold uppercase tracking-wider text-ink-700">
                        {{ pref.category }}
                      </span>
                      @if (pref.priority === 'critical' || pref.priority === 'high') {
                        <span class="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider"
                              [class.bg-escalation-bg]="pref.priority === 'critical'"
                              [class.text-escalation-text]="pref.priority === 'critical'"
                              [class.bg-brand-teal-soft]="pref.priority === 'high'"
                              [class.text-brand-teal]="pref.priority === 'high'">
                          {{ pref.priority }}
                        </span>
                      }
                    </div>
                    <p class="text-[13px] leading-snug">{{ pref.detail }}</p>
                  </div>
                } @empty {
                  <div class="px-5 py-6 text-center text-[13px] text-ink-500">No preferences captured.</div>
                }
              </div>

              <!-- Risk assessments -->
              <div class="overflow-hidden rounded-xl border border-ink-200 bg-white">
                <div class="flex items-center border-b border-ink-200 px-5 py-3">
                  <h3 class="font-display text-[14.5px] font-semibold">Risk assessments</h3>
                </div>
                @for (r of p.risk_assessments; track r.id) {
                  <div class="border-b border-ink-100 px-5 py-3 last:border-b-0">
                    <div class="mb-1 flex items-center justify-between">
                      <span class="font-semibold capitalize">{{ r.assessment_type.replace('_', ' ') }}</span>
                      <span class="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider"
                            [class.bg-escalation-bg]="r.level === 'critical' || r.level === 'high'"
                            [class.text-escalation-text]="r.level === 'critical' || r.level === 'high'"
                            [class.bg-brand-teal-soft]="r.level === 'medium'"
                            [class.text-brand-teal]="r.level === 'medium'"
                            [class.bg-accent-soft]="r.level === 'low'"
                            [class.text-accent-hover]="r.level === 'low'">
                        {{ r.level }}
                      </span>
                    </div>
                    <p class="mb-1 text-[13px] leading-snug">{{ r.controls }}</p>
                    @if (r.review_due) {
                      <div class="text-[11.5px] text-ink-500">Review due {{ formatDate(r.review_due) }}</div>
                    }
                  </div>
                } @empty {
                  <div class="px-5 py-6 text-center text-[13px] text-ink-500">No risk assessments on file.</div>
                }
              </div>

              <!-- Restrictive practices -->
              <div class="col-span-2 overflow-hidden rounded-xl border border-ink-200 bg-white">
                <div class="flex items-center border-b border-ink-200 px-5 py-3">
                  <h3 class="font-display text-[14.5px] font-semibold">Restrictive practices register</h3>
                </div>
                @for (rp of p.restrictive_practices; track rp.id) {
                  <div class="border-b border-ink-100 px-5 py-3 last:border-b-0">
                    <div class="mb-1 flex items-center gap-2">
                      <span class="font-semibold capitalize">{{ rp.practice_type.replace('_', ' ') }}</span>
                      <span class="rounded-full bg-ink-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-ink-700">
                        {{ rp.status }}
                      </span>
                    </div>
                    @if (rp.authorisation_ref) {
                      <div class="text-[12px] text-ink-500">
                        Auth: {{ rp.authorisation_ref }} · {{ formatDate(rp.authorised_from) }} → {{ formatDate(rp.authorised_to) }}
                      </div>
                    }
                    @if (rp.notes) {
                      <p class="mt-1 text-[13px] leading-snug">{{ rp.notes }}</p>
                    }
                  </div>
                } @empty {
                  <div class="px-5 py-6 text-center text-[13px] text-ink-500">No restrictive practices recorded.</div>
                }
              </div>

              <!-- Open incidents -->
              @if (p.open_incidents.length > 0) {
                <div class="col-span-2 overflow-hidden rounded-xl border border-escalation-text/40 bg-escalation-bg/40">
                  <div class="border-b border-escalation-text/20 px-5 py-3">
                    <h3 class="font-display text-[14.5px] font-semibold text-escalation-text">Open incidents</h3>
                  </div>
                  @for (inc of p.open_incidents; track inc.id) {
                    <div class="border-b border-escalation-text/10 px-5 py-3 last:border-b-0">
                      <div class="mb-1 flex items-center gap-2">
                        <span class="font-semibold">{{ inc.summary }}</span>
                        <span class="rounded-full bg-white px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-escalation-text">
                          {{ inc.incident_type }} · {{ inc.category.replace('_', ' ') }}
                        </span>
                      </div>
                      <div class="text-[12px] text-ink-500">
                        {{ formatDateTime(inc.occurred_at) }} · {{ inc.location || 'no location' }}
                      </div>
                    </div>
                  }
                </div>
              }
            </div>
          }

          <!-- HISTORY — audit log feed -->
          @if (tab() === 'history') {
            <h3 class="mb-3 font-display text-[15px] font-semibold">Recent changes</h3>
            <p class="mb-4 text-[12.5px] text-ink-500">
              Audit-log entries for records linked to this participant (plans, goals, contacts, shifts, clinical records).
            </p>
            @if (p.recent_changes.length > 0) {
              <div class="overflow-hidden rounded-xl border border-ink-200 bg-white">
                <table class="w-full text-[13.5px]">
                  <thead>
                    <tr class="border-b border-ink-200 bg-ink-100 text-[11px] font-bold uppercase tracking-wider text-ink-500">
                      <th class="px-5 py-2.5 text-left">When</th>
                      <th class="px-5 py-2.5 text-left">Record</th>
                      <th class="px-5 py-2.5 text-left">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (c of p.recent_changes; track c.record_id + c.changed_at) {
                      <tr class="border-b border-ink-100 last:border-b-0">
                        <td class="px-5 py-3">
                          <div class="font-semibold">{{ formatDateTime(c.changed_at) }}</div>
                        </td>
                        <td class="px-5 py-3">
                          <div class="capitalize">{{ c.table.replace('_', ' ') }}</div>
                          <div class="font-mono text-[11px] text-ink-500">{{ c.record_id.slice(0, 8) }}…</div>
                        </td>
                        <td class="px-5 py-3">
                          <span class="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider"
                                [class.bg-accent-soft]="c.action === 'INSERT'"
                                [class.text-accent-hover]="c.action === 'INSERT'"
                                [class.bg-brand-teal-soft]="c.action === 'UPDATE'"
                                [class.text-brand-teal]="c.action === 'UPDATE'"
                                [class.bg-escalation-bg]="c.action === 'DELETE'"
                                [class.text-escalation-text]="c.action === 'DELETE'">
                            {{ c.action }}
                          </span>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            } @else {
              <div class="rounded-xl border border-dashed border-ink-200 px-5 py-8 text-center text-[13px] text-ink-500">
                No recorded changes yet.
              </div>
            }
          }
        } @else {
          <div class="py-10 text-center text-[13px] text-ink-500">Loading…</div>
        }
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ParticipantDetailComponent implements OnInit {
  private participants = inject(ParticipantService);
  private router = inject(Router);

  readonly id = input.required<string>();
  readonly data = signal<ParticipantDetail | null>(null);
  readonly tab = signal<Tab>('overview');

  readonly tabList = computed(() => {
    const d = this.data();
    return [
      { key: 'overview' as Tab, label: 'Overview', count: undefined as number | undefined },
      { key: 'contacts' as Tab, label: 'Contacts', count: d?.contacts.length ?? 0 },
      { key: 'plan' as Tab, label: 'Plan & Goals', count: this.activeGoalCount() },
      {
        key: 'services' as Tab,
        label: 'Services',
        count: (d?.upcoming_shifts.length ?? 0) + (d?.recent_shifts.length ?? 0),
      },
      {
        key: 'clinical' as Tab,
        label: 'Clinical',
        count:
          (d?.medications.length ?? 0) +
          (d?.preferences.length ?? 0) +
          (d?.risk_assessments.length ?? 0),
      },
      { key: 'history' as Tab, label: 'History', count: d?.recent_changes.length ?? 0 },
    ];
  });

  readonly activeGoalCount = computed(
    () => this.data()?.goals.filter((g) => g.status === 'active').length ?? 0,
  );
  readonly achievedGoalCount = computed(
    () => this.data()?.goals.filter((g) => g.status === 'achieved').length ?? 0,
  );
  readonly pausedGoalCount = computed(
    () => this.data()?.goals.filter((g) => g.status === 'paused').length ?? 0,
  );

  async ngOnInit() {
    try {
      const detail = await this.participants.get(this.id());
      this.data.set(detail);
    } catch {
      this.data.set(null);
    }
  }

  initials(p: ParticipantDetail): string {
    return ((p.first_name[0] ?? '') + (p.last_name[0] ?? '')).toUpperCase();
  }

  initialsFromName(name: string): string {
    return name
      .split(/\s+/)
      .map((n) => n[0] ?? '')
      .join('')
      .slice(0, 2)
      .toUpperCase();
  }

  formatDate(iso: string | null): string {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  formatDateTime(iso: string | null): string {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString('en-AU', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }

  formatTime(iso: string | null): string {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleTimeString('en-AU', { hour: '2-digit', minute: '2-digit', hour12: false });
  }

  openChat(_p: ParticipantDetail) {
    // Could pre-seed the chat session with participant_id later; for now just navigate.
    this.router.navigate(['/chat']);
  }
}

# PLAN — Special Care Australia AI Care Assistant

This is the single working plan for the SCA Care Assistant. It combines the original NDIS schema plan and the SPA "Coming Soon" sequencing plan into one document, split into two sections:

- **[Implemented](#implemented)** — work already shipped, dated, with what landed.
- **[Planned](#planned)** — work not yet started, in the order we intend to do it, with backend + frontend scope per phase.

The deeper schema and API references live in [`CLAUDE.md`](./CLAUDE.md) and [`DB_Design.md`](./DB_Design.md). This file is the *plan*; those are the *spec*.

---

## Context

The customer-service-agent project replaced its generic e-commerce demo tables (`orders`, `accounts`, `faq_entries`) with a real **system of record** for Special Care Australia, an NDIS-registered disability support provider. The chatbot answers questions about participants, their NDIS plans, scheduled supports, goals, and progress notes, against a schema that must satisfy NDIS Practice Standards and Quality & Safeguards Commission audit expectations from day one.

**Locked decisions (do not re-litigate):**

- **System of record** — primary store for participants, plans, shifts, notes, incidents.
- **Exclude billing entirely** — no rate cards, no NDIS support-item pricing codes, no claim generation, no plan-budget allocated/spent tracking. Brevity/Lumary/etc. handle billing externally.
- **Full compliance from day 1** — immutable progress notes, incident reports (reportable + general), restrictive practices register, medication records, audit log via Postgres triggers on all clinical/safeguarding tables.

**Out of scope / explicit non-goals:**

- Billing, rate cards, claim generation, NDIS portal integration.
- Multi-tenancy. Schema is SCA-only; tenancy isolation is a separate project.
- Rostering automation, staff availability calendars, leave management.
- Document storage backend (S3/blob wiring). `documents.storage_url` is a string pointer.

---

# Implemented

Everything in this section is shipped, in `main`, exercised by tests, and reflected in `CLAUDE.md` and `DB_Design.md`. Dates are when the work landed.

## Phase 1 — Core people + chat linkage ✅ Shipped 2026-05 / -06

Replaced the e-commerce tables with the people domain.

- New tables: `participants`, `contacts`, `staff`, `participant_staff_assignments`, `service_types`, `knowledge_articles`.
- `sessions` gained nullable `participant_id` + `staff_id` FKs.
- Dropped `orders`, `accounts`, `faq_entries` + their tools.
- Seed data, audit triggers on the new tables, chat tools `lookup_participant`, `search_knowledge`, `get_contacts`.

## Phase 2 — Plans + goals + service agreements ✅ Shipped 2026-06-03

- New tables: `plans`, `goals`, `plan_goals` (M:M), `service_agreements`.
- Goals belong to the participant (survive plan renewal); `current_plan_id` points at the plan currently funding them.
- Tools: `get_active_plan`, `get_goals`.

## Phase 3 — Service delivery ✅ Shipped 2026-06-03

- New table: `shifts` (scheduled/actual times, status, cancellation reason, optional `handover_note_id` linking back to a progress note).
- Bidirectional FK between `shifts.handover_note_id` and `progress_notes.shift_id` resolved with `use_alter=True`.
- Tools: `get_upcoming_shifts`, `get_recent_shifts`.
- Tests in `tests/test_shifts.py`.

## Phase 4 — Clinical + safeguarding ✅ Shipped 2026-06-03

- New tables: `progress_notes`, `incidents`, `incident_followups`, `medication_records`, `medication_administration_log`, `restrictive_practices`, `risk_assessments`, `participant_preferences`, `documents`.
- **Two immutability triggers verified in Postgres**: `progress_notes_immutability_trigger` (blocks UPDATE/DELETE when `locked_at IS NOT NULL`) and `med_admin_immutability_trigger` (blocks UPDATE/DELETE unconditionally). Corrections happen via a new `progress_notes` row with `corrects_note_id` pointing at the original.
- Tools: `get_preferences`, `get_medications`, `get_participant_changes`.
- Tests in `tests/test_clinical.py` (in-memory) + `tests/test_immutability.py` (Postgres-only, skipped by default).

## Phase 5 — Auth ✅ Shipped 2026-06-04

- New tables: `users` (scrypt password hash, role enum, optional `staff_id` / `participant_id` linkage) + `auth_sessions` (opaque Bearer tokens, 7-day TTL).
- `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`.
- All API routes gated via `Depends(current_user)` / `Depends(current_staff)`; participant role can only see their own record.
- Frontend HTTP interceptor + SPA route guards + 401-redirects-to-login.
- Seed creates 6 user accounts (1 admin + 2 staff + 3 participants), all with dev password `ChangeMe!2026`.
- 16 tests in `tests/test_auth.py`.

## Phase 6 — Frontend admin SPA ✅ Shipped 2026-06-03

- Angular 20 standalone components, signals, Tailwind v3.
- Login → Dashboard → Participant list → Participant detail (Overview / Contacts / Plan & Goals / Services / Clinical / History tabs) → Chat.
- All routes lazy-loaded.
- SPA fallback in `app/main.py` (`SPAStaticFiles` + `spa_fallback_handler`) so direct-URL navigation to `/login`, `/participants/:id`, etc. works while XHR clients still get proper JSON errors.

## Phase 7 — Participant write UI ✅ Shipped 2026-06-04

Removed the read-only constraint on the participant pages.

- **Backend**: `POST /participants` (staff-only, 409 on duplicate live `ndis_number`, 400 on bad enum with allowed values listed). `PATCH /participants/{id}` via Pydantic `exclude_unset` (empty body → 400, bad enum → 400, missing id → 404, duplicate live `ndis_number` → 409).
- **Frontend**: `/participants/new` and `/participants/:id/edit` components mirroring each other. Dashboard's "+ New participant" button and participant detail's "Edit profile" button route to them.
- End-to-end verified via curl across all error codes; both buttons live in the browser.

## Phase 8 — Chat session owner scoping ✅ Shipped 2026-06-04

Closed the gap where any logged-in user could see any other user's chat history.

- **Backend**: `sessions.user_id` FK → `users.id` (indexed, `SET NULL` on delete). Stamped on create by `POST /sessions` and the `/chat` + `/chat/stream` agent paths from `current_user.id`. `repo.list_sessions(user_id, include_escalated)` is now scope-mandatory — empty scope returns empty results.
- **Rule**: everyone sees only the sessions they created. `UserRole.ADMIN` additionally sees every session with `status = escalated` across users (cross-user oversight).
- **Reads vs writes**: the admin escalated-override is read-only. `POST /chat`, `POST /chat/stream`, and `DELETE /sessions/{id}` always 403 when the caller doesn't own the session — admins observe escalations, they don't impersonate the chatter.
- Two new repo tests (`test_scope_filters_to_owner`, `test_admin_view_includes_escalated_across_users`) plus end-to-end curl verification with three real logins.
- DB volume reset + reseeded for the new column.

## Phase 9 — Dead-button sweep ✅ Shipped 2026-06-04

Audited every visible button in the SPA. Fixed three live ones; marked the rest as explicit "Soon" affordances so nothing reads as broken.

- **Dashboard header search** — was a no-op input. Now submits on Enter to `/participants?search=…`; `participant-list` hydrates `search` / `status` signals from `queryParamMap` on init.
- **"+ Add goal"** on participant-detail Plan tab — converted from a dead button to a disabled "Soon" pill matching the sidebar pattern. Real CRUD planned as Phase A below.
- **Mobile hamburger** on chat-view header — removed; there's no mobile drawer behind it and the sidebar is `hidden md:flex`. Reinstate when a real mobile layout exists.

## Cross-cutting: triggers, soft-delete, audit

- **Audit trigger** (`audit_trigger_func()`) writes to `audit_log` on every INSERT/UPDATE/DELETE for 18 audited tables across Phases 1–4 plus `users`. Soft-delete (setting `deleted_at`) is itself an UPDATE so the deletion is auditable.
- **Skipped audit** (intentional): `service_types`, `knowledge_articles`, `participant_preferences`, `sessions`, `messages`, `auth_sessions`.
- **Soft-delete tables**: `participants`, `contacts`, `staff`, `plans`, `service_agreements`, `medication_records`, `documents`, `users`. Live rows have `deleted_at IS NULL`. Unique constraints use partial indexes so re-creating a row after soft-delete is possible.
- **Never soft-deleted**: `progress_notes` (locked is append-with-corrections), `incidents` / `incident_followups` (close with status), `medication_administration_log` (immutable). Chat (`sessions` / `messages`) uses `status = 'closed'` rather than deletion.

## Cross-cutting: Alembic baseline ✅ Shipped 2026-06-04

- `alembic.ini` + async `alembic/env.py` reading `DATABASE_URL` from `app.config` + a no-op `0001_baseline.py` marking the current schema as head.
- `init_db()` still calls `Base.metadata.create_all` on startup. Switching to `alembic upgrade head` is queued for after real data lands (see Planned · Operational).

---

# Planned

Two clusters: **SPA feature phases** (the "Coming Soon" sidebar items, plus goal CRUD and attachments) and **Operational debt** (production-readiness items).

The recommended path: ship **Phase A** alone next — it removes the most visually broken affordance (the + Add goal pill) without taking on storage decisions or new top-level routes. A → B → C → D is a natural "fill out the sidebar" arc, each independently shippable. E is sequenced last because it depends on a storage-backend decision that's separate.

## Phase A — Goal CRUD (next — smallest, highest leverage)

**Why first.** Goals are the most visible write affordance on the participant detail page. They're already modelled (`goals` + `plan_goals` join). The Plan tab on participant-detail already lists them; only create/edit/archive is missing.

**Backend.**
- `POST /participants/{id}/goals` — create. Payload: `description`, `category`, `target_date?`, attach to current plan via `plan_goals` (funding_category + priority).
- `PATCH /goals/{id}` — partial update (description, target_date, status — including `achieved` / `paused`).
- `DELETE /goals/{id}` — soft delete (set `status = removed`; row is audited via existing trigger).
- New `GoalCreateRequest` + `GoalUpdateRequest` Pydantic models in `app/api/models.py`.
- Repo: `create_goal`, `update_goal`, `archive_goal` in `app/memory/repository.py`.
- Tests in `tests/test_goals.py` covering create + update + archive + audit trigger fires.

**Frontend.**
- Replace the disabled "+ Add goal" pill on `participant-detail.ts` with an active button → opens an inline `<dialog>` form (or routes to `/participants/:id/goals/new`).
- Per-goal row gets a kebab menu: Edit / Mark achieved / Pause / Remove.
- `GoalService` with `create / update / archive` on `services/goal.service.ts`.
- After mutate, reload `participants.get(id)` to refresh the tab (cheap; same call already drives the page).

**Done when:** staff user can create a goal from the Plan tab, edit its description and target date, mark it achieved, and remove it. Each mutation appears in the History tab via the existing audit trigger.

## Phase B — Plans & Goals top-level page

**Why.** Sidebar Plans & Goals leads here. Aggregated view across all participants — useful for plan managers and coordinators looking at expiring plans, plans with no active goals, etc.

**Backend.**
- `GET /plans` — list with filters `status`, `management_type`, `expiring_within_days`, cursor pagination.
- `GET /plans/{id}` — detail (participant, goals on the plan, service agreements).
- `POST /plans` + `PATCH /plans/{id}` — create + update (staff only).
- `POST /plans/{id}/goals` — attach an existing goal via `plan_goals` join.

**Frontend.**
- `/plans` route under admin shell — table: plan number, participant, period, mgmt type, status, days remaining.
- Filter chips (Active / Draft / Expired / Expiring ≤30d).
- `/plans/:id` detail — header + linked goals + service agreements.
- Promote the sidebar item from disabled `<div>` to active `<a routerLink="/plans">`.

**Done when:** sidebar Plans & Goals navigates, lists every plan with filters, and clicking through opens a detail page that mirrors the participant detail's Plan tab.

## Phase C — Staff page

**Why.** Sidebar Staff leads here. Staff roster + compliance dates (NDIS Worker Check, WWCC, police check expiries) is a real safeguarding need — flag rows where any check expires inside 30 days.

**Backend.**
- `GET /staff` already exists (list). Add filters `role`, `status`, `expiring_within_days` (covering any of the three check fields).
- `GET /staff/{id}` — detail with assigned participants (`participant_staff_assignments`).
- `POST /staff` + `PATCH /staff/{id}` — create + update (admin/manager only).
- Add `current_admin_or_manager` dep in `app/auth/dependencies.py`.

**Frontend.**
- `/staff` route — table: name, role, status, NDIS Worker Check expiry (badge if ≤30d), WWCC expiry, Police check expiry.
- `/staff/:id` detail — profile + check expiries + currently-assigned participants.
- `/staff/new` + `/staff/:id/edit` mirroring participant new/edit pattern.
- Promote sidebar Staff to active.

**Done when:** sidebar Staff lists active staff with expiry badges, admin/manager can add/edit a staff row, expiring checks are obvious at a glance.

## Phase D — Knowledge base page

**Why.** Knowledge articles already power the chat agent's `search_knowledge` tool. A staff-facing browse + author UI lets non-engineers curate the corpus the chatbot answers from — closing the loop between escalations and content.

**Backend.**
- `GET /knowledge` already exists (list). Add filters `category`, `status`, `q` (full-text or LIKE on title + body_md).
- `GET /knowledge/{id}` — single article with rendered markdown body.
- `POST /knowledge` + `PATCH /knowledge/{id}` — create + update (admin/manager only).
- Tags are already JSON-arrayed; expose as a chip editor.

**Frontend.**
- `/knowledge` route — list grouped by category, with status (draft / published / archived) filter.
- `/knowledge/:id` — rendered article (reuse `marked + DOMPurify` from chat).
- `/knowledge/new` + `/knowledge/:id/edit` — title, category, tags (chip input), markdown body (textarea + side-by-side preview).
- Promote sidebar Knowledge base to active.

**Done when:** staff can browse and search articles, draft/publish/archive them, and the chat agent's answers continue to reflect the published-status articles via the unchanged `search_knowledge` tool.

## Phase E — Message attachments (chat composer paperclip)

**Why last in the SPA work.** Depends on the `documents` storage backend, which is explicitly out of scope today (`documents.storage_url` is just a string pointer with no S3/blob wiring). Without that decision the paperclip is a dead promise. Don't ship until the backend exists.

**Pre-requisite (separate decision, not in this phase):**
- Pick storage: S3 / GCS / Azure Blob. Bias toward S3 + boto3 to match Australian-region NDIS expectations.
- Add `STORAGE_BUCKET`, `STORAGE_REGION`, `AWS_ACCESS_KEY_ID` / `SECRET` to settings.
- Implement `app/storage.py` with `upload(file, key) → storage_url` + `signed_url(key, ttl) → str`.

**Backend.**
- `POST /documents` (multipart) — upload, save row to `documents` (uses existing polymorphic `subject_type` + `subject_id`), return signed URL.
- `GET /documents/{id}` — return signed URL (TTL ~15min).
- Attach-to-chat: `POST /messages/{id}/attachments` linking documents to the user-turn that referenced them.

**Frontend.**
- Composer paperclip → file picker, upload via `POST /documents`, show inline chip with filename + clear button before send.
- On send, include attachment ids in the chat request payload.
- Assistant rendering: show attached file chips on the user-message bubble.

**Done when:** staff can attach a PDF/image to a chat message, the document persists with a `documents.storage_url`, and clicking it opens a signed URL.

## Operational debt (parallel to A–E)

Production-readiness items. Not user-facing features, but they all need to land before any real participant data does. None depends on any other (modulo the password-rotation timing).

- **Switch `init_db()` from `create_all` to `alembic upgrade head`** — baseline is in place; flip the switch once real data lands.
- **Rotate the seed password.** `ChangeMe!2026` is in source and must not survive to production.
- **Audit-log attribution to current user.** `audit_log` captures *what* changed, not *who*. Push `current_user.id` into a Postgres session variable (`SET LOCAL "app.user_id" = ...`) inside the `get_db` dependency and stamp `changed_by` from the trigger.
- **Rate-limiting `/auth/login`** — FastAPI middleware (slowapi or hand-rolled) before any production deploy.
- **Password reset / MFA / SSO.** Staff SSO (Microsoft / Google) is the highest-leverage next step.
- **Mobile responsive layout.** Sidebar is `hidden md:flex`, no mobile drawer; the chat-view hamburger was removed because it had no destination. Build the drawer and reinstate the trigger.
- **Production deployment config.** No Dockerfile for the app, no env-var injection beyond `.env`, no health-check probe wiring, no CSRF posture documented.

## Verification per phase

1. New routes work end-to-end via curl: 201 on create, 200 on update, 403 on participant role where applicable, 404 on missing id, 409 on uniqueness collisions.
2. Audit-log entries appear in the History tab for any new write (relies on existing per-table triggers).
3. Sidebar item promoted from disabled `<div>` to active `<a>` only after the page is real — never ship the navigation ahead of the destination.
4. `pytest -v` passes (roughly 16 new tests per phase: create + update + delete + 403 + 409 + audit fires + list filter).
5. Frontend build is green; new lazy chunk is named after the route (e.g. `chunk-…-plans-list`).

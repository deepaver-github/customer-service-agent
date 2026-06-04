# Database Design — Special Care Australia Care Assistant

This document describes the database schema for the Special Care Australia (SCA) Care Assistant application. The database is the **system of record** for SCA operations — participants, plans, shifts, notes, incidents — with billing intentionally excluded (handled by external software).

The schema rolled out in four phases — **all four are now live**. An auth layer (`users` + `auth_sessions`) was added after Phase 4. The phase a table belongs to is marked in each section.

---

## 1. Conventions

- **DB engine:** PostgreSQL 16. Tests use SQLite 3 (in-memory). Postgres-specific features (triggers, partial indexes) degrade gracefully on SQLite.
- **Primary keys:** UUID v4, stored as `VARCHAR(36)`. Generated either client-side (`uuid.uuid4()` in SQLAlchemy defaults) or server-side (`gen_random_uuid()::text` in triggers).
- **Timestamps:** `TIMESTAMP WITH TIME ZONE`, default `now()` UTC. `created_at` set on insert; `updated_at` set on insert + auto-bumped on update via SQLAlchemy `onupdate`.
- **Soft delete:** nullable `deleted_at TIMESTAMPTZ` column on participant/plan/staff/document/agreement-type tables. Live rows have `deleted_at IS NULL`. Never applied to clinical records (`progress_notes`, `incidents`) — those are corrected, not deleted.
- **Enums:** stored as Postgres `ENUM` types (SQLAlchemy `Enum(SomeEnum)`), Python-side as `str, enum.Enum`. Enum values use snake_case.
- **Foreign keys:** explicit `ON DELETE` clause on every FK. Cascade for parent→child operational data; `RESTRICT` for clinical authorship; `SET NULL` for optional linkage (e.g. session ↔ participant).
- **Money:** none. Billing is out of scope.

---

## 2. ER Overview

```
                              ┌──────────────┐
                              │   sessions   │── participant_id ──┐
                              │   messages   │── staff_id ────┐   │
                              └──────────────┘                │   │
                                                              ▼   ▼
   ┌────────────┐         ┌────────────┐         ┌────────────┐
   │   staff    │◄────────│ participant_│────────►│participants│
   └─────┬──────┘   many  │_staff_      │  many   └──────┬─────┘
         │          ─many │_assignments│                 │
         │                └────────────┘                 │ 1:N
         │                                               │
         │ 1:N            ┌──────────────┐               │
         │                │   contacts   │◄──────────────┤
         │                └──────────────┘               │
         │                                               │
         │           Phase 2 ✅ ────────────────────────│
         │                ┌─────────┐    ┌────────┐      │
         │                │  plans  │───►│ goals  │◄─────┤
         │                └─────────┘    └────────┘      │
         │                     ▲         plan_goals (M:M)│
         │                     │                         │
         │           Phase 3 ✅ ─────────────────────────│
         │                ┌────────────┐                 │
         │                │  shifts    │◄────────────────┤
         │                └─────┬──────┘                 │
         │                      │                        │
         │           service_types ─────► service_agreements ◄──┤
         │                                                      │
         │           Phase 4 ✅ ───────────────────────────────│
         │                ┌─────────────────┐                   │
         └──── author ───►│ progress_notes  │◄──────────────────┤
                          │ incidents       │                   │
                          │ medication_*    │                   │
                          │ restrictive_*   │                   │
                          │ risk_assessments│                   │
                          │ participant_    │                   │
                          │  _preferences   │                   │
                          │ documents       │                   │
                          └─────────────────┘                   │
                                                                │
                          Auth ✅                                │
                          ┌──────────────┐                      │
                          │    users     │── staff_id ──────────┤
                          │              │── participant_id ────┤
                          └──────┬───────┘                      │
                                 │ 1:N                          │
                          ┌──────▼────────┐                     │
                          │ auth_sessions │  (Bearer tokens,    │
                          └───────────────┘   7-day TTL)        │
                                                                │
                          ┌──────────────┐                      │
                          │ knowledge_   │   (no FK to anything)│
                          │  _articles   │                      │
                          └──────────────┘                      │
                                                                │
                          ┌──────────────┐                      │
                          │  audit_log   │  (populated by       │
                          └──────────────┘   Postgres triggers) │
```

---

## 3. Tables

### 3.1 Chat (Phase 1 — live)

#### `sessions`
Chat session between a user and the assistant. Always attributed to the logged-in user via `user_id` (the owner column used for scoping); `participant_id` and `staff_id` remain for chat-on-behalf-of semantics.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | UUID v4 |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default now(), auto-bump | |
| `metadata` | JSON | nullable | Free-form, reserved for future use |
| `status` | ENUM `sessionstatus` | NOT NULL, default `active` | `active` / `escalated` / `closed` |
| `participant_id` | VARCHAR(36) | FK → participants(id) ON DELETE SET NULL, nullable | Chat-on-behalf-of pointer |
| `staff_id` | VARCHAR(36) | FK → staff(id) ON DELETE SET NULL, nullable | Operational team-member pointer |
| `user_id` | VARCHAR(36) | FK → users(id) ON DELETE SET NULL, nullable, indexed | **Owner column.** Stamped on session create (POST /sessions and the agent paths) from `current_user.id`. Drives the GET /sessions scope filter. |

**Index:** `ix_sessions_user_id (user_id)` for owner-scoped listing.

Audit: **no** (high-churn, low safeguarding value).

**Scoping rule.** `repo.list_sessions(user_id, include_escalated)` is scope-mandatory — passing neither returns an empty list, so a caller can't accidentally leak rows. `GET /sessions` always passes `user_id = current_user.id` and sets `include_escalated=True` only when `current_user.role == ADMIN`. Reads and writes via the per-id routes apply the same rule; the admin escalated-override is read-only.

#### `messages`
Individual turns within a session. Content is stored as raw JSON to preserve Anthropic's tool-use / tool-result block structure.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `session_id` | VARCHAR(36) | FK → sessions(id) ON DELETE CASCADE, NOT NULL | |
| `role` | VARCHAR(20) | NOT NULL | `user` / `assistant` / `tool` / `user_with_tool_result` |
| `content` | JSON | NOT NULL | Either a string or a list of content blocks |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() | |

Audit: no.

---

### 3.2 Audit log (Phase 1 — live)

#### `audit_log`
Append-only change log. Populated entirely by Postgres triggers (no Python writes). See §4 for trigger details.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | `gen_random_uuid()::text` |
| `table_name` | VARCHAR(50) | NOT NULL | e.g. `participants` |
| `record_id` | VARCHAR(36) | NOT NULL | The audited row's `id` |
| `action` | ENUM `auditaction` | NOT NULL | `INSERT` / `UPDATE` / `DELETE` |
| `old_values` | JSON | nullable | `row_to_json(OLD)` — null on INSERT |
| `new_values` | JSON | nullable | `row_to_json(NEW)` — null on DELETE |
| `changed_at` | TIMESTAMPTZ | NOT NULL, default now() | |

**Index suggestion (Phase 2+):** `(table_name, record_id, changed_at DESC)` to support per-record history lookups.

---

### 3.3 People (Phase 1 — live)

#### `participants`
A person SCA supports.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `ndis_number` | VARCHAR(20) | unique among live rows (see index) | Some NDIS numbers have leading zeros — keep as string |
| `first_name` | VARCHAR(100) | NOT NULL | |
| `last_name` | VARCHAR(100) | NOT NULL | |
| `preferred_name` | VARCHAR(100) | nullable | |
| `dob` | DATE | nullable | |
| `primary_disability_category` | ENUM `disabilitycategory` | nullable | `intellectual`, `autism`, `psychosocial`, `physical`, `sensory`, `neurological`, `acquired_brain_injury`, `other` |
| `communication_needs` | TEXT | nullable | Plain-English description |
| `address_line1` / `address_line2` | VARCHAR(255) | nullable | |
| `suburb` | VARCHAR(100) | nullable | |
| `state` | ENUM `australianstate` | nullable | `ACT`/`NSW`/`NT`/`QLD`/`SA`/`TAS`/`VIC`/`WA` |
| `postcode` | VARCHAR(10) | nullable | |
| `phone` | VARCHAR(30) | nullable | |
| `email` | VARCHAR(255) | nullable | |
| `status` | ENUM `participantstatus` | NOT NULL, default `onboarding` | `onboarding`/`active`/`paused`/`exited` |
| `created_at` / `updated_at` | TIMESTAMPTZ | standard | |
| `deleted_at` | TIMESTAMPTZ | nullable | Soft delete |

**Indexes:**
- `ix_participants_ndis_number_live` — UNIQUE partial: `(ndis_number) WHERE deleted_at IS NULL` (Postgres-only; SQLite falls back to a non-partial unique).

Audit: **yes**.

#### `contacts`
Family, support coordinator, plan manager, GP, advocate, emergency contact, etc. (`relationship` is the column name — Python attribute is `relationship_type` to avoid clashing with SQLAlchemy's `relationship()` function.)

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `participant_id` | VARCHAR(36) | FK → participants ON DELETE CASCADE, NOT NULL | |
| `name` | VARCHAR(200) | NOT NULL | |
| `relationship` | ENUM `contactrelationship` | NOT NULL | `family`/`guardian`/`support_coordinator`/`plan_manager`/`gp`/`advocate`/`emergency`/`other` |
| `phone` | VARCHAR(30) | nullable | |
| `email` | VARCHAR(255) | nullable | |
| `is_primary` | BOOLEAN | NOT NULL, default false | |
| `is_emergency` | BOOLEAN | NOT NULL, default false | |
| `notes` | TEXT | nullable | |
| `created_at` | TIMESTAMPTZ | standard | |
| `deleted_at` | TIMESTAMPTZ | nullable | Soft delete |

Audit: **yes**.

#### `staff`
Support workers, coordinators, managers, clinical leads.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `first_name` / `last_name` | VARCHAR(100) | NOT NULL | |
| `email` / `phone` | nullable | | |
| `role` | ENUM `staffrole` | NOT NULL, default `support_worker` | `support_worker`/`coordinator`/`manager`/`clinical_lead` |
| `ndis_worker_check_expiry` | DATE | nullable | |
| `wwcc_expiry` | DATE | nullable | Working With Children Check |
| `police_check_expiry` | DATE | nullable | |
| `qualifications` | TEXT | nullable | Free text |
| `status` | ENUM `staffstatus` | NOT NULL, default `active` | `active`/`on_leave`/`inactive` |
| `created_at` / `updated_at` | TIMESTAMPTZ | standard | |
| `deleted_at` | TIMESTAMPTZ | nullable | Soft delete |

Audit: **yes** — worker-screening dates being silently edited is exactly what NDIS Commission auditors look for.

#### `participant_staff_assignments`
Many-to-many: which staff are allocated, secondary, or **do not roster** for which participant. Surrogate `id` is required so the audit trigger (which uses `NEW.id`/`OLD.id`) works.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `participant_id` | VARCHAR(36) | FK → participants ON DELETE CASCADE, NOT NULL | |
| `staff_id` | VARCHAR(36) | FK → staff ON DELETE RESTRICT, NOT NULL | |
| `assignment_type` | ENUM `assignmenttype` | NOT NULL | `primary`/`secondary`/`do_not_roster` |
| `valid_from` | DATE | NOT NULL | |
| `valid_to` | DATE | nullable | Open-ended assignments use NULL |
| `notes` | TEXT | nullable | |
| `created_at` | TIMESTAMPTZ | standard | |

Audit: **yes** — `do_not_roster` flags are safeguarding-critical.

---

### 3.4 Service catalog (Phase 1 — live)

#### `service_types`
SCA's offering catalog. No rates (billing excluded).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `code` | VARCHAR(50) | UNIQUE, NOT NULL | Slug, e.g. `sil`, `personal_care` |
| `name` | VARCHAR(200) | NOT NULL | Human-readable |
| `description` | TEXT | nullable | |
| `ndis_category` | ENUM `ndiscategory` | NOT NULL, default `core` | `core`/`capacity_building`/`capital` — informational only |
| `status` | ENUM `servicetypestatus` | NOT NULL, default `active` | `active`/`archived` |
| `created_at` | TIMESTAMPTZ | standard | |

Audit: no (slow-moving catalog).

---

### 3.5 Knowledge base (Phase 1 — live)

#### `knowledge_articles`
The chatbot's reference content — services overview, NDIS basics, onboarding, complaints process.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `title` | VARCHAR(255) | NOT NULL | |
| `body_md` | TEXT | NOT NULL | Markdown |
| `category` | ENUM `knowledgecategory` | NOT NULL, default `other` | `about_services`/`ndis_basics`/`getting_started`/`supports_explained`/`complaints_feedback`/`other` |
| `tags` | JSON | nullable | Array of strings |
| `status` | ENUM `knowledgestatus` | NOT NULL, default `published` | `draft`/`published`/`archived` |
| `created_at` / `updated_at` | TIMESTAMPTZ | standard | |

Audit: no (content edits are not safeguarding-relevant).

---

### 3.6 Funding & goals (Phase 2 — live)

#### `plans`
An NDIS plan, dated. A participant can have multiple plans over time; one is current.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `participant_id` | VARCHAR(36) | FK → participants ON DELETE CASCADE, NOT NULL | |
| `plan_number` | VARCHAR(50) | unique among live rows | |
| `start_date` / `end_date` | DATE | NOT NULL | |
| `management_type` | ENUM `managementtype` | NOT NULL | `self`/`plan_managed`/`agency_managed` |
| `plan_manager_name` | VARCHAR(200) | nullable | |
| `plan_manager_contact` | VARCHAR(255) | nullable | Phone or email |
| `status` | ENUM `planstatus` | NOT NULL, default `draft` | `draft`/`active`/`expired` |
| `deleted_at` | TIMESTAMPTZ | nullable | |

Audit: **yes**.

#### `goals`
Goals belong to the **participant**, not the plan, so they survive plan renewals.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `participant_id` | VARCHAR(36) | FK → participants ON DELETE CASCADE, NOT NULL | |
| `current_plan_id` | VARCHAR(36) | FK → plans, nullable | Plan currently funding the goal |
| `description` | TEXT | NOT NULL | |
| `category` | ENUM `goalcategory` | NOT NULL | `independence`/`community`/`employment`/`health`/`relationships`/`learning`/`other` |
| `target_date` | DATE | nullable | |
| `status` | ENUM `goalstatus` | NOT NULL, default `active` | `active`/`achieved`/`paused`/`removed` |
| `created_at` / `updated_at` | TIMESTAMPTZ | standard | |

Audit: **yes**.

#### `plan_goals`
Many-to-many join: which goals are funded under which plan (with funding category and priority).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | Surrogate (required for audit trigger) |
| `plan_id` | VARCHAR(36) | FK → plans ON DELETE CASCADE, NOT NULL | |
| `goal_id` | VARCHAR(36) | FK → goals ON DELETE CASCADE, NOT NULL | |
| `funding_category` | ENUM `ndiscategory` | NOT NULL | `core`/`capacity_building`/`capital` |
| `priority` | INTEGER | NOT NULL, default 0 | |

Audit: **yes**.

#### `service_agreements`
Written agreement between SCA and a participant describing which supports we'll deliver. Doesn't model rates or units — just scope.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `participant_id` | VARCHAR(36) | FK → participants, NOT NULL | |
| `service_type_id` | VARCHAR(36) | FK → service_types, NOT NULL | |
| `valid_from` | DATE | NOT NULL | |
| `valid_to` | DATE | nullable | |
| `scope_notes` | TEXT | nullable | |
| `status` | ENUM `agreementstatus` | NOT NULL, default `draft` | `draft`/`active`/`ended` |
| `deleted_at` | TIMESTAMPTZ | nullable | |

Audit: **yes**.

---

### 3.7 Service delivery (Phase 3 — planned)

#### `shifts`
A scheduled or delivered support. Not a billing record — a roster + activity record.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `participant_id` | VARCHAR(36) | FK → participants, NOT NULL | |
| `staff_id` | VARCHAR(36) | FK → staff, nullable | Null = unassigned |
| `service_type_id` | VARCHAR(36) | FK → service_types, NOT NULL | |
| `service_agreement_id` | VARCHAR(36) | FK → service_agreements, nullable | Soft enforcement |
| `scheduled_start` / `scheduled_end` | TIMESTAMPTZ | NOT NULL | |
| `actual_start` / `actual_end` | TIMESTAMPTZ | nullable | Filled on completion |
| `location` | TEXT | nullable | |
| `status` | ENUM `shiftstatus` | NOT NULL, default `scheduled` | `scheduled`/`in_progress`/`completed`/`cancelled_by_participant`/`cancelled_by_provider`/`no_show` |
| `cancelled_reason` | TEXT | nullable | |
| `cancelled_by_staff_id` | VARCHAR(36) | FK → staff, nullable | |
| `handover_note_id` | VARCHAR(36) | FK → progress_notes, nullable | Link to handover for next shift |
| `created_at` / `updated_at` | TIMESTAMPTZ | standard | |

Audit: **yes**.

---

### 3.8 Clinical & safeguarding (Phase 4 — planned)

#### `progress_notes`
Append-with-corrections. Once `locked_at` is set, the row is immutable (enforced by a Postgres trigger). To correct a locked note, insert a new note with `corrects_note_id` referencing the original.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `participant_id` | VARCHAR(36) | FK → participants, NOT NULL | |
| `author_staff_id` | VARCHAR(36) | FK → staff ON DELETE RESTRICT, NOT NULL | Authorship must survive staff deletion |
| `shift_id` | VARCHAR(36) | FK → shifts, nullable | |
| `incident_id` | VARCHAR(36) | FK → incidents, nullable | |
| `note_type` | ENUM `notetype` | NOT NULL | `shift_note`/`clinical_observation`/`family_communication`/`incident_related`/`handover`/`goal_progress` |
| `content` | TEXT | NOT NULL | |
| `corrects_note_id` | VARCHAR(36) | self-FK, nullable | Points to the note being corrected |
| `locked_at` | TIMESTAMPTZ | nullable | When set, row is immutable |
| `locked_by_staff_id` | VARCHAR(36) | FK → staff, nullable | |
| `created_at` | TIMESTAMPTZ | standard | |

**No `deleted_at`** — locked clinical notes are never deleted.
Audit: **yes**. Immutability: **yes** (see §4).

#### `incidents`
Reportable + general incidents. NDIS Commission notification timestamps are recorded for audit.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `participant_id` | VARCHAR(36) | FK → participants, NOT NULL | |
| `reporter_staff_id` | VARCHAR(36) | FK → staff, NOT NULL | |
| `shift_id` | VARCHAR(36) | FK → shifts, nullable | |
| `incident_type` | ENUM `incidenttype` | NOT NULL | `reportable`/`general` |
| `category` | ENUM `incidentcategory` | NOT NULL | `abuse`/`neglect`/`restrictive_practice_unauthorised`/`medication_error`/`injury`/`near_miss`/`complaint`/`behaviour_concern`/`property_damage`/`other` |
| `occurred_at` | TIMESTAMPTZ | NOT NULL | |
| `location` | TEXT | nullable | |
| `summary` | TEXT | NOT NULL | |
| `description` | TEXT | NOT NULL | |
| `immediate_action_taken` | TEXT | nullable | |
| `status` | ENUM `incidentstatus` | NOT NULL, default `open` | `open`/`investigating`/`resolved`/`closed` |
| `ndis_commission_notified_at` | TIMESTAMPTZ | nullable | |
| `worksafe_notified_at` | TIMESTAMPTZ | nullable | |
| `police_notified_at` | TIMESTAMPTZ | nullable | |
| `notification_reference` | TEXT | nullable | Reference numbers from regulators |
| `created_at` / `updated_at` | TIMESTAMPTZ | standard | |

**No `deleted_at`** — close with status, never disappear.
Audit: **yes**.

#### `incident_followups`
Per-incident action log.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `incident_id` | VARCHAR(36) | FK → incidents ON DELETE CASCADE, NOT NULL | |
| `staff_id` | VARCHAR(36) | FK → staff, NOT NULL | |
| `action_taken` | TEXT | NOT NULL | |
| `outcome` | TEXT | nullable | |
| `follow_up_due_date` | DATE | nullable | |
| `completed_at` | TIMESTAMPTZ | nullable | |
| `created_at` | TIMESTAMPTZ | standard | |

Audit: **yes**.

#### `medication_records`
Current medications for a participant.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `participant_id` | VARCHAR(36) | FK → participants, NOT NULL | |
| `medication_name` | VARCHAR(200) | NOT NULL | |
| `dose` | VARCHAR(100) | NOT NULL | |
| `route` | ENUM `medicationroute` | NOT NULL | `oral`/`topical`/`injection`/`inhalation`/`other` |
| `frequency` | VARCHAR(100) | NOT NULL | Free text |
| `prescriber` | VARCHAR(200) | nullable | |
| `start_date` | DATE | NOT NULL | |
| `end_date` | DATE | nullable | |
| `prn` | BOOLEAN | NOT NULL, default false | "As required" |
| `notes` | TEXT | nullable | |
| `status` | ENUM `medicationstatus` | NOT NULL, default `active` | `active`/`discontinued` |
| `deleted_at` | TIMESTAMPTZ | nullable | |

Audit: **yes**.

#### `medication_administration_log`
Per-dose record. **Immutable** — once inserted, cannot be UPDATEd or DELETEd.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `medication_record_id` | VARCHAR(36) | FK → medication_records, NOT NULL | |
| `participant_id` | VARCHAR(36) | FK → participants, NOT NULL | Denormalised for fast lookups |
| `administered_by_staff_id` | VARCHAR(36) | FK → staff ON DELETE RESTRICT, NOT NULL | |
| `shift_id` | VARCHAR(36) | FK → shifts, nullable | |
| `administered_at` | TIMESTAMPTZ | NOT NULL | |
| `dose_given` | VARCHAR(100) | NOT NULL | |
| `was_witnessed` | BOOLEAN | NOT NULL, default false | |
| `witness_staff_id` | VARCHAR(36) | FK → staff, nullable | |
| `notes` | TEXT | nullable | |
| `created_at` | TIMESTAMPTZ | standard | |

Audit: **yes**. Immutability: **yes** (unconditional).

#### `restrictive_practices`
Authorisation register. Even with no restraints in use, the table holds a `none_authorised` row per participant.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `participant_id` | VARCHAR(36) | FK → participants, NOT NULL | |
| `practice_type` | ENUM `restrictivepractice` | NOT NULL | `environmental`/`chemical`/`mechanical`/`physical`/`seclusion`/`none_authorised` |
| `authorisation_ref` | VARCHAR(100) | nullable | NDIS authorisation reference |
| `authorised_from` / `authorised_to` | DATE | nullable | |
| `behaviour_support_plan_doc_id` | VARCHAR(36) | FK → documents, nullable | |
| `status` | ENUM `practicestatus` | NOT NULL | `active`/`expired`/`revoked` |
| `notes` | TEXT | nullable | |
| `created_at` / `updated_at` | TIMESTAMPTZ | standard | |

Audit: **yes**.

#### `risk_assessments`
Versioned per participant per assessment_type.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `participant_id` | VARCHAR(36) | FK → participants, NOT NULL | |
| `assessment_type` | ENUM `risktype` | NOT NULL | `manual_handling`/`choking`/`behavioural`/`environmental`/`community_access`/`medication`/`other` |
| `level` | ENUM `risklevel` | NOT NULL | `low`/`medium`/`high`/`critical` |
| `controls` | TEXT | NOT NULL | Free text |
| `assessor_staff_id` | VARCHAR(36) | FK → staff, NOT NULL | |
| `assessed_at` | TIMESTAMPTZ | NOT NULL | |
| `review_due` | DATE | nullable | |
| `superseded_by_id` | VARCHAR(36) | self-FK, nullable | Versioning chain |

Audit: **yes**.

#### `participant_preferences`
Likes, dislikes, triggers, routine notes — critical for SIL handover. One row per preference.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `participant_id` | VARCHAR(36) | FK → participants ON DELETE CASCADE, NOT NULL | |
| `category` | ENUM `preferencecategory` | NOT NULL | `communication`/`food`/`routine`/`sensory`/`trigger`/`like`/`dislike` |
| `detail` | TEXT | NOT NULL | |
| `priority` | ENUM `preferencepriority` | NOT NULL, default `normal` | `critical`/`high`/`normal` |
| `created_at` / `updated_at` | TIMESTAMPTZ | standard | |

Audit: no (high-churn, low-risk).

#### `documents`
Pointer table. Actual file content lives in object storage (S3/blob); this table holds metadata. Polymorphic subject: a document belongs to a participant OR a staff member.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | |
| `subject_type` | ENUM `documentsubject` | NOT NULL | `participant`/`staff` |
| `subject_id` | VARCHAR(36) | NOT NULL | UUID (no FK because polymorphic) |
| `document_type` | ENUM `documenttype` | NOT NULL | `ndis_plan`/`service_agreement`/`consent`/`id_document`/`medical`/`qualification`/`police_check`/`wwcc`/`behaviour_support_plan`/`risk_assessment`/`other` |
| `title` | VARCHAR(255) | NOT NULL | |
| `storage_url` | TEXT | NOT NULL | Pointer to S3/blob; actual backend is out of scope for now |
| `mime_type` | VARCHAR(100) | nullable | |
| `size_bytes` | BIGINT | nullable | |
| `uploaded_by_staff_id` | VARCHAR(36) | FK → staff, NOT NULL | |
| `expiry_date` | DATE | nullable | For time-bound docs (checks, qualifications) |
| `created_at` | TIMESTAMPTZ | standard | |
| `deleted_at` | TIMESTAMPTZ | nullable | |

Audit: **yes**.

---

## 4. Triggers (Postgres-only)

Defined in `app/memory/database.py` and applied during `init_db()`.

### 4.1 Audit trigger

A single trigger function `audit_trigger_func()` writes to `audit_log` on every INSERT/UPDATE/DELETE for the tables listed below. The function reads `NEW.id` / `OLD.id` directly — every audited table MUST have a column literally named `id`.

```sql
CREATE OR REPLACE FUNCTION audit_trigger_func() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (id, table_name, record_id, action, old_values, new_values, changed_at)
        VALUES (gen_random_uuid()::text, TG_TABLE_NAME, NEW.id, 'INSERT', NULL, row_to_json(NEW), now());
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (...)
        VALUES (..., TG_TABLE_NAME, NEW.id, 'UPDATE', row_to_json(OLD), row_to_json(NEW), now());
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (...)
        VALUES (..., TG_TABLE_NAME, OLD.id, 'DELETE', row_to_json(OLD), NULL, now());
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;
```

**Audited tables:**

| Table | Phase | Reason |
|---|---|---|
| `participants` | 1 ✅ | Identifying info, status changes |
| `contacts` | 1 ✅ | Emergency-contact integrity |
| `staff` | 1 ✅ | Worker-screening dates |
| `participant_staff_assignments` | 1 ✅ | `do_not_roster` is safeguarding-critical |
| `plans` | 2 ✅ | Funding scope changes |
| `goals` | 2 ✅ | Outcomes accountability |
| `plan_goals` | 2 ✅ | Funding category changes |
| `service_agreements` | 2 ✅ | Scope of service |
| `shifts` | 3 | Delivery record |
| `progress_notes` | 4 | Clinical record |
| `incidents` | 4 | Compliance-critical |
| `incident_followups` | 4 | Compliance-critical |
| `medication_records` | 4 | Clinical |
| `medication_administration_log` | 4 | Clinical |
| `restrictive_practices` | 4 | NDIS Commission |
| `risk_assessments` | 4 | Compliance |
| `documents` | 4 | Document register integrity |
| `users` | Auth ✅ | Account lifecycle, role changes |

**Not audited** (high-churn or low safeguarding value): `sessions`, `messages`, `service_types`, `knowledge_articles`, `participant_preferences`, `auth_sessions`, `audit_log` itself.

### 4.2 Immutability trigger (Phase 4 — live)

Two cases:

- **`progress_notes`**: raise an exception on UPDATE/DELETE when `OLD.locked_at IS NOT NULL`. Corrections are made by inserting a new row with `corrects_note_id` pointing at the original.
- **`medication_administration_log`**: raise an exception on UPDATE/DELETE unconditionally (no edit window).

Function shape:

```sql
CREATE OR REPLACE FUNCTION enforce_immutability() RETURNS TRIGGER AS $$
BEGIN
    IF TG_TABLE_NAME = 'medication_administration_log' THEN
        RAISE EXCEPTION 'medication_administration_log rows are immutable';
    ELSIF TG_TABLE_NAME = 'progress_notes' AND OLD.locked_at IS NOT NULL THEN
        RAISE EXCEPTION 'progress_notes row is locked and cannot be modified';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

---

## 5. Soft delete

Tables with `deleted_at`: `participants`, `contacts`, `staff`, `plans`, `service_agreements`, `medication_records`, `documents`.

- Setting `deleted_at = now()` is an UPDATE — the audit trigger fires, so the deletion itself is audit-logged.
- Repository methods filter on `deleted_at IS NULL` by default. To restore, set `deleted_at = NULL`.
- Unique constraints (e.g. `participants.ndis_number`) are enforced via **partial unique indexes** so that re-creating a participant with the same NDIS number is possible after a soft-delete.

Tables that **never** soft-delete:

- `progress_notes` — locked rows are append-with-corrections, not delete.
- `incidents` / `incident_followups` — close with status; never disappear from operational view.
- `medication_administration_log` — immutable.
- Chat (`sessions` / `messages`) — closed sessions use `status = 'closed'` rather than deletion.

---

## 6. Phase status

| Phase | Tables | Status |
|---|---|---|
| **1 — Core people + chat linkage** | sessions (+ FKs), messages, audit_log, participants, contacts, staff, participant_staff_assignments, service_types, knowledge_articles | ✅ Live |
| **2 — Funding & goals** | plans, goals, plan_goals, service_agreements | ✅ Live |
| **3 — Service delivery** | shifts | ✅ Live |
| **4 — Clinical & safeguarding** | progress_notes, incidents, incident_followups, medication_records, medication_administration_log, restrictive_practices, risk_assessments, participant_preferences, documents | ✅ Live |
| **Post-Phase 4 — Auth** | users, auth_sessions | ✅ Live |

---

## 7. Auth tables (post-Phase 4 — live)

### 7.1 `users`

Authentication identity. One row per login. Each user is optionally linked to either a `staff` row (team members) or a `participant` row (self-service); admin users have neither FK set.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID (VARCHAR 36) | PK | |
| `email` | VARCHAR(255) | partial unique among `deleted_at IS NULL` | Lowercased on login lookup. |
| `password_hash` | VARCHAR(500) | NOT NULL | `scrypt$<n>$<r>$<p>$<salt_hex>$<key_hex>` encoding. |
| `role` | ENUM `user_role` | NOT NULL DEFAULT `support_worker` | `admin` / `manager` / `coordinator` / `support_worker` / `participant`. |
| `staff_id` | UUID (VARCHAR 36) | nullable FK → `staff(id)` ON DELETE SET NULL | Set for team-member logins. |
| `participant_id` | UUID (VARCHAR 36) | nullable FK → `participants(id)` ON DELETE SET NULL | Set for participant self-service logins. |
| `is_active` | BOOLEAN | NOT NULL DEFAULT TRUE | Disable without deleting. |
| `last_login_at` | TIMESTAMPTZ | nullable | Stamped on successful login. |
| `created_at` / `updated_at` / `deleted_at` | TIMESTAMPTZ | standard | Soft-delete supported. |

**Index:** `ix_users_email_live UNIQUE (email) WHERE deleted_at IS NULL`.

**Role helper.** `STAFF_ROLES = {admin, manager, coordinator, support_worker}` — `participant` is intentionally excluded; routes guarded by `Depends(current_staff)` 403 it.

### 7.2 `auth_sessions`

Opaque Bearer tokens. Lookup-by-token is O(1) (PK), revoke is a single UPDATE, expiry is a comparison — no JWT key rotation, no symmetric secret.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `token` | VARCHAR(96) | PK | `secrets.token_urlsafe(48)` — 64 chars. |
| `user_id` | UUID (VARCHAR 36) | NOT NULL FK → `users(id)` ON DELETE CASCADE | |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| `expires_at` | TIMESTAMPTZ | NOT NULL | Default TTL 7 days. |
| `revoked_at` | TIMESTAMPTZ | nullable | Set on `/auth/logout`. |

**Index:** `ix_auth_sessions_user (user_id)` for "list active sessions for user".

**Intentionally not audited.** High-churn, security-sensitive, no compliance reason to retain old tokens in `audit_log`.

### 7.3 Route-layer policy

| Route | Required role | Notes |
|---|---|---|
| `POST /auth/login` | none | Constant-time-ish: always runs `verify_password` against a dummy hash on email-miss to flatten timing. |
| `POST /auth/logout` / `GET /auth/me` | any authenticated | |
| `GET /participants`, `/staff`, `/knowledge`, `/dashboard/stats` | `STAFF_ROLES` | `participant` role → 403. |
| `POST /participants` | `STAFF_ROLES` | Create. 409 on duplicate live `ndis_number`, 400 on bad enum (with allowed values), 201 on success. |
| `GET /participants/{id}` | staff *or* own record | `participant_can_access()` enforces self-only. |
| `PATCH /participants/{id}` | `STAFF_ROLES` | Partial update via Pydantic `exclude_unset`. Empty body → 400, bad enum → 400 with allowed values, missing id → 404, duplicate live `ndis_number` → 409. |
| `POST /sessions`, `POST /chat`, `POST /chat/stream` | any authenticated | Stamps `sessions.user_id = current_user.id`. `participant` users get their `participant_id` auto-pinned to themselves on session create. Chat writes 403 unless caller owns the session. |
| `GET /sessions` | any authenticated | Scoped to caller (`user_id == current_user.id`). For `admin`, additionally returns every session with `status = escalated` across users. |
| `GET /sessions/{id}` | any authenticated | 403 unless caller owns it or (`admin` AND `status = escalated`). |
| `DELETE /sessions/{id}` | any authenticated | 403 unless caller owns it. Admin override does NOT extend to writes. |

### 7.4 Seed credentials (dev only)

The seed creates 6 users with the password `ChangeMe!2026`:

- `admin@specialcareaust.example` (admin)
- `maria.lo@specialcareaust.example` (coordinator → Maria Lo)
- `tom.s@specialcareaust.example` (support_worker → Tom Schultz)
- `aisha.p@example.com` (participant → Aisha Patel)
- `ben.n@example.com` (participant → Benjamin Nguyen)
- `chloe.r@example.com` (participant → Chloe Ramirez)

**Rotate before any real data lands.** The password is in source.

---

## 8. Migrations

The project ships `Base.metadata.create_all()` on app startup (`app/memory/database.py:init_db()`) and a no-op Alembic baseline (`alembic/versions/0001_baseline.py`). Schema evolution before real data lands:

```bash
docker compose down -v          # wipes the volume — data lost
docker compose up -d
python -m app.memory.seed       # creates tables + triggers + users, inserts NDIS samples
```

Once real participant data lands: `alembic stamp head` to mark the current state, then `alembic revision --autogenerate -m "..."` + `alembic upgrade head` for every change. Drop the `create_all` call from `init_db()` at that point.

---

## 9. Out of scope

- **Billing / NDIS claims** — no rate cards, no plan_budgets with allocated/spent, no claim CSV generation. Handled by external software (Brevity/Lumary/etc.) that ingests our shift records.
- **Audit-log attribution to current user** — we capture *what* changed, not *who*. Needs `SET LOCAL "app.user_id" = ...` per request so triggers can stamp `changed_by`.
- **MFA, SSO, password reset, rate-limiting `/auth/login`** — auth ships with email+password + Bearer tokens only.
- **Multi-tenancy** — schema is SCA-only.
- **Object storage backend** — `documents.storage_url` is a pointer; S3/blob wiring is a separate decision.
- **Rostering automation, staff availability, leave management** — separate domain.
- **Real-time NDIS portal integration** — separate domain.

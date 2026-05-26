# Promotion plan: Team kickoff checklist

**Source:** `./original-flatpack.html`
**Manifest version:** 0.1.0
**Date:** 2026-05-26
**Prepared by:** Promotion-time agent following `prompts/promote-flatpack.md`

Every claim in this plan is labelled with one of three confidence tiers:

- **MANIFEST-ASSERTED** — taken directly from the Flatpack's
  `<script type="application/json" id="flatpack-manifest">` block. Trust it.
- **CODE-INFERRED** — extracted by reading the JS. Reliable for behaviour,
  worth a second pass with the user.
- **INTERVIEW-REQUIRED** — the Flatpack does not answer this. Asked of the
  user during the promotion conversation.

---

## Why this is being promoted **INTERVIEW-REQUIRED**

A consulting firm has been using a project-kickoff Flatpack for
client engagements over the past six months. Each consultant ran
their own copy locally, sent the printable summary to the client
afterwards, and that was the end of it. As of last month:

- Three consultants are working two engagements each, simultaneously.
- The partner has asked "how many engagements have completed kickoff
  this quarter, and what did the notes say?"
- A new template version was drafted (added "regulatory check"
  section). Distributing it via Slack hasn't worked; one consultant
  is still on v1.

Three of the manifest's `promotionSignals` are now firing:

1. **Multiple people work the same checklist at the same time** —
   not literally on the same instance, but the firm wants visibility
   across all instances.
2. **Checklist templates need to be edited centrally and rolled out
   to teams; versioning matters** — the regulatory-check rollout
   exposed the absence of any rollout mechanism.
3. **Per-user attribution or sign-off is required** — implicit in
   the partner's "what did the notes say" question; once attribution
   is needed, who-ticked-what becomes audit-relevant.

The fourth trigger (cross-project progress tracking, where the
entity is now `Project` with checklists as children) is not firing
yet, but is visible on the horizon — the partner's quarterly view
is exactly that question.

## Archetype and recipe mapping

Archetype (from manifest): `workflow-with-checklist` **MANIFEST-ASSERTED**

Recommended Baseplate recipes (composed per `docs/flatpack-archetype-to-recipe-map.md`):

- `admin-users` — always-applies for this archetype. Each consultant
  is a named user; the partner is an admin.
- `audit-log` — always-applies. Records who-ticked-what,
  template-version-changes, and run-status transitions.
- A status-workflow recipe — *not yet written* in Baseplate (listed
  in `docs/recipes/README.md`'s future-recipes). Custom for v1.

Gaps not covered by any current Baseplate recipe:

- Versioned `ChecklistTemplate` storage and the rollout flow
  (creating a new template version, optionally migrating in-progress
  runs).
- The per-run `Progress` shape (done/note per item, with attribution).

## Entities

### `ChecklistTemplate` **CODE-INFERRED**

The Flatpack's `checklist` constant is a hardcoded array. The
Baseplate version factors it out as a versioned database entity so
templates can be edited centrally.

| Field | Type | Constraints |
|---|---|---|
| `id` | uuid | primary key |
| `name` | string | required |
| `version` | integer | required; monotonically increasing per `name` |
| `is_active` | boolean | required; default true; only one active per `name` |
| `created_by_id` | uuid | FK → users.id; required |

Indexes:

- `UNIQUE (name, version)` — natural composite key.

### `ChecklistSection` **MANIFEST-ASSERTED**

Mirrors the Flatpack manifest's `ChecklistSection` entity verbatim.

| Field | Type | Constraints |
|---|---|---|
| `id` | string | required; unique within the template |
| `template_id` | uuid | FK → checklist_templates.id; required |
| `title` | string | required |
| `position` | integer | required; ordering within the template |

### `ChecklistItem` **MANIFEST-ASSERTED**

Mirrors the Flatpack manifest's `ChecklistItem` entity verbatim.

| Field | Type | Constraints |
|---|---|---|
| `id` | string | required; unique within the template |
| `section_id` | string | FK → checklist_sections.id; required |
| `text` | string | required |
| `why` | string | optional (explanatory text) |

### `ChecklistRun` **INTERVIEW-REQUIRED**

One walk-through of one template version, tied to a project name
(or other handle) and the consultant running it. The Flatpack's
`state.progress` map becomes a child of this entity.

| Field | Type | Constraints |
|---|---|---|
| `id` | uuid | primary key |
| `template_id` | uuid | FK → checklist_templates.id; required |
| `template_version` | integer | required; snapshot at run-start |
| `owner_id` | uuid | FK → users.id; required |
| `project_handle` | string | required; free-text identifier (e.g. "Acme Q2 kickoff") |
| `status` | enum | `in_progress` / `completed` / `abandoned`; default `in_progress` |
| `started_at` | datetime | required |
| `completed_at` | datetime | nullable; set when status → completed |

### `ChecklistProgress` **CODE-INFERRED**

One row per (run, item). The Flatpack stored this as
`state.progress[item.id] = { done, note }`; the Baseplate version
makes attribution and timing explicit.

| Field | Type | Constraints |
|---|---|---|
| `id` | uuid | primary key |
| `run_id` | uuid | FK → checklist_runs.id; required |
| `item_id` | string | required (refers to `ChecklistItem.id`) |
| `done` | boolean | required; default false |
| `note` | text | nullable |
| `done_by_id` | uuid | FK → users.id; nullable |
| `done_at` | datetime | nullable; set when done flips to true |

Constraint: `UNIQUE (run_id, item_id)`.

## Roles **INTERVIEW-REQUIRED**

- **Admin** (partner). Manages templates (CRUD, versioning,
  activation). Sees all runs across all consultants. Sees the
  audit log.
- **Consultant**. Creates and runs checklists for their own
  engagements. Can see other consultants' runs (read-only — the
  partner wants visibility, so does the team).

Open question: should consultants be able to *create* new
templates, or is that admin-only? Plan assumes admin-only for v1.

## Required features

| Feature | Tier | Notes |
|---|---|---|
| Auth (named users + login) | MANIFEST-ASSERTED (via promotion signal) | Recipe: `admin-users` |
| Persistent storage for Template, Section, Item, Run, Progress | MANIFEST-ASSERTED + CODE-INFERRED | Implied by entities |
| Template CRUD with versioning | INTERVIEW-REQUIRED | Custom code; not a recipe |
| "Start a new run from this template" endpoint | CODE-INFERRED | Mirrors the Flatpack's "load page" boot path |
| Per-item tick endpoint (PATCH progress) | CODE-INFERRED | Mirrors the Flatpack's checkbox handler |
| Per-item note edit endpoint | CODE-INFERRED | Mirrors the Flatpack's textarea handler |
| Run summary endpoint (progress, open items) | MANIFEST-ASSERTED | `exports: markdown` becomes a server-side render of the run |
| Markdown export of a run | MANIFEST-ASSERTED | Carry-over from `toMarkdown` in the Flatpack |
| Audit log: tick, untick, template-version change, run-status change | INTERVIEW-REQUIRED | Recipe: `audit-log` |
| Print-friendly run summary | MANIFEST-ASSERTED | Frontend concern; out of scope for the backend-only scaffold |

## Validation rules (carry-over from manifest)

Verbatim from the Flatpack's manifest:

- `every item belongs to exactly one section` **MANIFEST-ASSERTED**
- `item ids are stable across edits (used as state keys)` **MANIFEST-ASSERTED**
- `done flag is per item; progress is derived` **MANIFEST-ASSERTED**

The third rule has a subtle implication on the Baseplate side: the
*Run* has no separate "done" state — its derived counters update when
underlying `Progress.done` flips. Implement counter caching on `Run`
to avoid N+1 queries on the queue view.

## Validation predicates (structured)

The Flatpack's manifest at v0.1.0 doesn't carry `validation_predicates`
(predicates were introduced in flatpack#1 after this manifest was
written). At promotion time we add what we can — but this case study
exposes a gap.

**What we add to the frozen Flatpack:**

```json
{ "field": "id",        "constraint": "required" },
{ "field": "title",     "constraint": "required" },
{ "field": "text",      "constraint": "required" },
{ "field": "sectionId", "constraint": "required" }
```

These target `ChecklistSection.id`, `ChecklistSection.title`,
`ChecklistItem.id`, `ChecklistItem.text`, `ChecklistItem.sectionId` —
all fields the manifest declares.

**What we cannot add (yet):**

The interesting validation rules in this archetype live on the
*promoted* entities — `ChecklistTemplate.name` required,
`ChecklistTemplate.version` gte 1, `ChecklistRun.project_handle`
required, `ChecklistRun.owner_id` required. None of these fields
appear in the Flatpack's manifest. They're declared in
`reference/promoted-entities.json` instead.

The current Baseplate verifier (`verify_promotion.py`) reads
`validation_predicates` from the manifest and only resolves them
against manifest-entity fields. It does not read predicates from
`promoted-entities.json`. Filed as a new bridge issue against
Baseplate: the predicate schema and the verifier should be
extended to cover promoted-entity predicates.

For now: the promoted entities' validation rules are enforced in
the Baseplate code (Pydantic schemas + DB constraints) and visible
to a human reading either `decisions.md` or the project README, but
not to the verifier.

## UI / screens

| Screen | Mirrors which Flatpack region | Tier |
|---|---|---|
| Template list (admin) | new — Flatpack has no template management | INTERVIEW-REQUIRED |
| Template editor (admin) | new | INTERVIEW-REQUIRED |
| Run queue (everyone) | new | INTERVIEW-REQUIRED |
| Run detail (the actual checklist) | the entire Flatpack page | CODE-INFERRED |
| Audit log viewer (admin) | new | INTERVIEW-REQUIRED |

Out of scope for the backend-only scaffold; documented in the
project's README under "What's deliberately not built yet".

## Test cases to carry over

Sourced from `FLATPACK:TEST_CASES`. These become backend unit tests.

| Flatpack test | Baseplate test target |
|---|---|
| `computeProgress counts done items` | `ChecklistRunService.compute_progress` |
| `toMarkdown includes section titles` | `ChecklistRunService.to_markdown` |
| `toMarkdown checks items that are marked done` | `ChecklistRunService.to_markdown` |

The bindEvents and loadState smoke tests are Flatpack-specific
DOM concerns and don't carry over.

Plus a new test the Flatpack couldn't have:

- **Cross-run isolation**: ticking an item in run A doesn't affect
  the same item in run B. This is automatic with the Run + Progress
  shape but worth pinning.

## Open questions for the user **INTERVIEW-REQUIRED**

1. Can consultants create their own templates, or is that admin-only?
   (Plan assumes admin-only.)
2. When a template is updated to v2 while there are v1 runs in
   progress, do those runs auto-migrate, stay on v1, or pause and
   force a decision? (Plan assumes stay on v1 — `template_version` is
   snapshotted at run-start.)
3. Can a tick be un-ticked? If so, does the audit log record both
   events, or just the latest? (Plan assumes yes, both logged.)
4. Should there be a "section-level sign-off" beyond per-item ticks?
   (Plan assumes no for v1.)
5. Does the partner's quarterly view need any data the run-summary
   endpoint can't already provide (per-engagement reports across
   runs, time-to-complete, etc.)? (Plan assumes no for v1; that's a
   v2 reports surface.)
6. Should past templates be visible to consultants for reference, or
   only the active version? (Plan assumes past templates remain
   visible.)

## What is explicitly out of scope

- Multi-tenancy. One firm. (If the firm grows to franchise this tool
  to others, that's a second promotion event.)
- A graphical template editor. Templates are edited via JSON or a
  basic form for v1.
- Slack / email notifications when a run completes. Possible v2.
- Per-engagement billing or time-tracking integration. Separate
  product surface.
- Migrating in-progress runs to a new template version. v1 keeps
  them frozen.

## Hand-off

Once this plan is approved:

1. Open a new Baseplate project (`flatpack-team-kickoff-example`).
2. Copy `./original-flatpack.html` and the seed template data into
   `reference/`. Also write `reference/promoted-entities.json` listing
   `ChecklistTemplate`, `ChecklistRun`, `ChecklistProgress` (the three
   code-inferred / interview-required entities).
3. Apply Baseplate recipes per the mapping above (admin-users at-base,
   audit-log stub).
4. Carry the validation rules and test cases into the new project's
   tests.
5. Run `make verify-promotion` and document any honest residuals in
   the project README.
6. Keep the Flatpack alive for fast local iteration and parity checks.

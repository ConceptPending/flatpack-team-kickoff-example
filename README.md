# Team kickoff — a Flatpack promoted into Baseplate

A second worked example of the [Flatpack](https://github.com/ConceptPending/flatpack) → [Baseplate](https://github.com/ConceptPending/baseplate)
promotion bridge. Where
[flatpack-invoice-review-example](https://github.com/ConceptPending/flatpack-invoice-review-example)
covered the `import-validate-store` archetype, this one covers
`workflow-with-checklist`.

Two worked examples make the pattern visible. One could be an
accident; two suggest a shape.

It is intentionally **not** a finished product. The point of the
exercise is to demonstrate, end-to-end, that the bridge works for a
different archetype.

## What's in this repo

```
backend/                  FastAPI app — fully working backend
  app/
    models/               ChecklistTemplate, ChecklistSection, ChecklistItem,
                          ChecklistRun, ChecklistProgress, AuditLog (stub)
    schemas/              Pydantic v2 schemas per entity
    services/             checklist_templates, runs (compute_progress + to_markdown)
    api/                  /api/admin/checklist-templates, /api/admin/runs
  alembic/versions/       Migration 003 promotes the schema
  tests/                  26 tests; carries over 3 named tests from the Flatpack
reference/                Preserved Flatpack artefacts
  original-flatpack.html    v0.1.0 checklist Flatpack, with predicates added at promotion
  promotion-plan.md         The plan with three confidence tiers
  promoted-entities.json    ChecklistTemplate / ChecklistRun / ChecklistProgress
  decisions.md              Answers to INTERVIEW-REQUIRED items
```

Frontend deliberately untouched from the Baseplate template — this is
a **backend-only** worked example.

## How this differs from invoice-review

| | invoice-review | team-kickoff |
|---|---|---|
| Archetype | `import-validate-store` | `workflow-with-checklist` |
| Recipes applied | admin-users + audit-log stub + adapted public-submission | admin-users + audit-log stub |
| Promotion's signature move | `supplier_name` → `Supplier` FK | hardcoded `checklist` array → versioned `ChecklistTemplate` |
| External-facing surface | CSV upload + downloads | Markdown export endpoint + tick API |
| Custom code not covered by a recipe | Cross-file dedup + currency normaliser | Template versioning + run snapshot of template_version |

Two important new pieces of code in this build are general enough
that they might become Baseplate recipes in future:

- **Versioned reference data + immutable runs.** Templates are
  versioned; runs snapshot the version at start.
- **Per-row attribution.** `ChecklistProgress.done_by_id` + `done_at`
  make ticking auditable per-row.

## The promotion journey

Following [`docs/promoting-a-flatpack.md`](https://github.com/ConceptPending/baseplate/blob/main/docs/promoting-a-flatpack.md)
in the Baseplate repo:

1. **Decided** — three of the Flatpack manifest's `promotionSignals`
   started firing: multi-consultant use, template rollout, per-user
   attribution. Narrative in
   [`reference/promotion-plan.md`](reference/promotion-plan.md).
2. **Analysed** — `tools/promote.mjs` on the Flatpack side filled
   the MANIFEST-ASSERTED sections of the plan; the agent walked
   CODE-INFERRED by reading the JS and INTERVIEW-REQUIRED by asking
   the user.
3. **Planned** — 5 entities (2 manifest + 3 promoted), recipe set
   (admin-users + audit-log stub), open questions, validation
   predicates limitation. See
   [`reference/promotion-plan.md`](reference/promotion-plan.md).
4. **Scaffolded** — this repo. Created from the Baseplate template
   via `gh repo create --template ConceptPending/baseplate` (the
   template flag was enabled when the first worked example surfaced
   that gap as baseplate#32).
5. **Preserved** — `reference/` stays on disk.

## Recipe application status

| Recipe | Applied | Note |
|---|---|---|
| `admin-users` | Yes (base) | Multi-admin already in the base; `is_admin` flag distinguishes partner from consultant. |
| `audit-log` | **Stubbed** | Table created (matches recipe model). Hooks at every event-emit site as `# TODO(audit-log-recipe)` markers in `app/services/`. Recipe walk is unfinished. |

## How to run

```bash
cp .env.example backend/.env
cp .env.example frontend/.env.local

make install
make hash-password           # paste output into backend/.env
make db
make migrate                 # applies migrations 001 + 002 + 003
make dev                     # backend on :8001

make verify-promotion        # 29 OK, 3 MISS, 5 WARN — see below
make test-backend            # 26 tests pass
```

## What the verifier flags — honestly

**29 OK**: most entity fields verify cleanly; all manifest predicates
that have manifest-entity targets resolve; manifest exports `json`
and `markdown` both have routes; 3 promoted entities + their fields
verified end-to-end.

**3 MISS** — all are legitimate semantic divergences, not bugs:

1. `entity ChecklistItem.sectionId` — the Flatpack uses JavaScript
   camelCase; the Baseplate model uses Python snake_case
   (`section_id`). Convention divergence at the language boundary.

2. `entity ChecklistItem.done` — the Flatpack had `done` directly
   on the item. The Baseplate version separates per-(run, item)
   state into `ChecklistProgress.done`. The data model is now
   correct for multi-user use.

3. `entity ChecklistItem.note` — same as `done`, moved to
   `ChecklistProgress`.

The MISSes (2) and (3) are the *whole point* of the promotion —
they represent the structural change that enables multi-user
attribution. A real CI gate would acknowledge them in
`reference/decisions.md` rather than treating them as failures.

**5 WARN** — all are honestly-unverifiable claims:

- 3 × type WARNs on `id` and `item_id` columns: the Flatpack used
  stable string keys; the Baseplate version uses database UUIDs.
  Documented decision (see
  [`reference/decisions.md`](reference/decisions.md) C).

- 1 × `export print_pdf`: client-side via `window.print()`; no
  server endpoint, correctly flagged.

- 1 × `predicate sectionId:required`: the predicate targets the
  manifest's camelCase field name; the model uses snake_case. Same
  divergence as MISS (1).

## What we learned (bridge issues filed and partially fixed)

Building this second worked example surfaced new bridge issues:

1. **`/markdown` wasn't in the export hint map.** Filed and fixed
   upstream in Baseplate during this build; verifier now matches
   `/markdown` routes for the `markdown` export.

2. **Predicates targeting promoted-entity fields aren't supported.**
   The Flatpack's `validation_predicates` only check manifest-entity
   fields; the interesting predicates for this archetype (e.g.
   `ChecklistRun.project_handle` required) live on promoted
   entities. Documented in the promotion plan as a known limitation,
   should be filed as a Baseplate enhancement.

3. **JS camelCase ↔ Python snake_case at the boundary.** The Flatpack
   uses `sectionId`; the Baseplate model uses `section_id`. The
   verifier matches field names literally and doesn't try to normalise.
   This is an honest naming-convention boundary; the right answer
   may be to canonicalise on snake_case in manifests (less convenient
   for the Flatpack's JS-native runtime) or for the verifier to
   accept both spellings.

## Related

- [Flatpack](https://github.com/ConceptPending/flatpack) — the spec
  and templates this Flatpack came from.
- [Flatpack case study](https://github.com/ConceptPending/flatpack/tree/main/case-studies/team-kickoff-promotion)
  — the source of the promotion plan in `reference/`.
- [First worked example: flatpack-invoice-review-example](https://github.com/ConceptPending/flatpack-invoice-review-example)
  — the `import-validate-store` archetype.
- [Baseplate](https://github.com/ConceptPending/baseplate) — the
  foundation this app sits on.
- [`docs/flatpack-archetype-to-recipe-map.md`](https://github.com/ConceptPending/baseplate/blob/main/docs/flatpack-archetype-to-recipe-map.md)
  — the canonical archetype → recipe set mapping.

## License

MIT, inherited from Baseplate.

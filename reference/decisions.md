# Promotion decisions log

Answers given to the `INTERVIEW-REQUIRED` items in
[`promotion-plan.md`](promotion-plan.md). Captured here so the
reasoning is traceable from the code back to the promotion event.

> This document is for the worked example. In a real promotion, the
> answers come from the actual partner + consultants — not from a
> notional exercise. Treat the answers below as illustrative.

## 1. Can consultants create templates, or admin-only?

**Answer:** Admin-only for v1.

**Implication:** Template-mutation routes (`POST /api/admin/checklist-templates`,
`PATCH .../activate`, etc.) gate on `is_admin`. Consultants get
read-only access to all templates plus full access to *runs* they own.
A future v2 might add a "draft a template" surface for consultants.

## 2. New template version while v1 runs are in progress — auto-migrate?

**Answer:** No. Snapshot `template_version` at run-start. v1 runs
stay on v1 even after v2 is activated.

**Implication:** `ChecklistRun.template_version` is required and
immutable. `ChecklistRunService.start()` reads the current active
version and writes it to the run. Subsequent template changes don't
touch existing progress rows.

## 3. Can a tick be un-ticked? Both events logged?

**Answer:** Yes, both logged.

**Implication:** `progress.ticked` and `progress.unticked` are both
audit events. When `done` flips false → true, set `done_by_id` and
`done_at`. When it flips true → false, **clear** both, *then* emit
the unticked audit event with the prior values in `extra`. This
keeps the source-of-truth clean (the row reflects current state)
while the audit log keeps the full timeline.

## 4. Section-level sign-off beyond per-item ticks?

**Answer:** No for v1.

**Implication:** No new entity, no `ChecklistSection.signed_off_by_id`
column. Section completion is derived from "all items done."

## 5. Partner's quarterly view — does it need data beyond run-summary?

**Answer:** No for v1. The partner can list runs by quarter,
filter by status, and read each run's summary endpoint.

**Implication:** No new reporting tables, no scheduled aggregations.
A simple `GET /api/admin/runs?status=completed&completed_after=...&completed_before=...`
suffices. v2 could add a per-engagement rollup.

## 6. Past templates visible to consultants, or only active?

**Answer:** Past templates remain visible (read-only).

**Implication:** `GET /api/admin/checklist-templates` returns all
versions, sorted by `(name, version)`. The list view can filter to
active-only by default.

---

## Decisions logged outside the plan

### A. The Flatpack's "blank progress on new items" migration

The Flatpack's `loadState()` migrates the stored progress map by
filling in any items that exist in the schema but aren't in storage.
The Baseplate version handles this differently: when a run is
*created*, the service writes one `Progress` row per template-version
item. Subsequent template changes don't add Progress rows — that's
the "no auto-migrate" decision from item 2.

If a user wanted "auto-add new items to in-progress runs" the
service-layer mechanism would be a new endpoint `POST
/api/admin/runs/{id}/sync-template` that compares the run's
`template_version` to the current active version and copies missing
items. Out of scope for v1.

### B. Why ChecklistSection / ChecklistItem are per-template-version

In the Flatpack, sections and items are global constants. In the
Baseplate version they're per-template-version so a template edit
creates new section/item rows alongside the new version. Older rows
remain immutable for the runs that snapshot them.

The alternative — global sections/items with versioning at a
different level — would have been less honest about the immutability
contract. Code-inferred from the "snapshot template_version at
run-start" decision.

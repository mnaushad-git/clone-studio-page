# Odoo Import Approval Gate

Phase 5 deliverable. Describes the machine-readable business approval mechanism that
must pass before `import_odoo_catalogue --apply` is allowed to write to Odoo.

## The approval file

[data/catalogue/catalogue-business-approvals.json](../../data/catalogue/catalogue-business-approvals.json)
holds one entry per business decision required before import, for exactly the
decisions CLAUDE.md Phase 5 names: `D03` (category codes), `D04` (product SKUs), `D08`
(tax/VAT treatment), `D09` (unit of measure — already `APPROVED`), `D10` (product
type), `D19` (opening inventory/availability posture).

Each entry:

```json
{
  "decision_id": "D03",
  "title": "Category codes",
  "proposed_value": { "...": "..." },
  "approved_value": null,
  "status": "PROPOSED",
  "approved_by": null,
  "approved_at": null,
  "approval_notes": "...",
  "evidence": { "...": "..." },
  "blocks_import": true
}
```

Allowed `status` values: `PROPOSED`, `APPROVED`, `REJECTED`, `REQUIRES_CLARIFICATION`.

## How a decision is approved

**Nothing in this codebase ever edits this file.** No script, CLI, or service writes
to `catalogue-business-approvals.json` — approving a decision means a human (with the
authority to make the business call) edits the JSON directly: sets `status` to
`APPROVED`, fills `approved_value` with the real decision, and fills `approved_by`/
`approved_at`. This is deliberate: "Do not auto-approve any decision" is a hard
constraint from the phase brief, enforced by omission (there is no write path) rather
than by a runtime check that could be bypassed.

## The gate itself

`app/services/catalogue/approval_gate.py`:

- `load_business_approvals(path) -> list[ApprovalDecision]` — reads and schema-validates
  the file. Raises `ApprovalFileError` on any structural problem (missing file, invalid
  JSON, missing required field, invalid `status` value, duplicate `decision_id`).
- `evaluate_approval_gate(decisions) -> ApprovalGateResult` — partitions decisions into
  `approved` / `unresolved` / `rejected` / `non_blocking`. A decision only counts as
  resolved if `blocks_import` is `False`, **or** `status == "APPROVED"` **and**
  `approved_value is not None`. A decision marked `APPROVED` with a still-null
  `approved_value` is treated as unresolved, not approved — this is the literal
  reading of CLAUDE.md Phase 5 §1: "Import apply mode must reject any decision where
  ... approved_value is null."
- `compute_approval_checksum(decisions) -> str` — a stable, order-independent SHA-256
  over every blocking decision's `(decision_id, status, approved_value)`. Stored on
  every `odoo_catalogue_import_runs` row (`approval_checksum`) so a later `--apply` can
  detect the approval file changed underneath a stale plan.

## check_catalogue_import_approvals CLI

```
python -m app.scripts.check_catalogue_import_approvals
python -m app.scripts.check_catalogue_import_approvals --json
```

Read-only, never modifies the approval file. Prints approved / unresolved / rejected /
non-blocking decisions. Exit code `0` only when every `blocks_import: true` decision is
`APPROVED` with a non-null `approved_value`; `1` if any blocking decision is unresolved
or rejected; `2` if the file itself can't be parsed/validated.

`import_odoo_catalogue --apply` calls the same `evaluate_approval_gate()` function
in-process (not by shelling out to the CLI) — the two can never disagree.

## Current status

As of this phase's implementation, running the checker against the real file reports:

```
Blocking decisions approved: 0
Unresolved decisions: 5   (D03, D04, D08, D10, D19 — all PROPOSED)
Rejected decisions: 0
Non-blocking decisions (informational): 1   (D09 — APPROVED)
```

`--apply` is refused until this changes.

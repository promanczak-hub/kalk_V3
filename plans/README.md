# plans/

Per-feature plan files. Each non-trivial change starts here **before code**.

## Convention

- One markdown file per planned change.
- Filename: kebab-case, descriptive (`add-pickup-body-type.md`, `fix-stage-6-color-correction.md`).
- Front-matter optional. Use sections: **Context**, **Approach**, **Critical files**, **Verification**, **Out of scope**.
- Once executed and merged, the plan file stays (history of *why*). It's not the same as `docs/audit/` (those are V1 specs).

## Relation to other planning surfaces

- `~/.claude/plans/` (global per-Claude-session plans) — where plan-mode auto-writes.
- This `plans/` (repo-scoped) — where committed, peer-reviewable plans live.
- `docs/audit/calc_*.md` — V1 reference specs (not plans).
- Memory files at `~/.claude/projects/D--kalk-v3/memory/MEMORY.md` — durable cross-session facts.

If you wrote a plan in `~/.claude/plans/` and the change is non-trivial, copy/move the relevant parts here so reviewers can see the *why*.

## Origin

This directory was introduced as part of the SUPERPOWERS-style discipline retrofit. See [Faza B3 of the overarching plan](../../../Users/proma/.claude/plans/spojrsysz-na-maja-apliakcje-flickering-patterson.md).

---
name: add-body-type
description: Add a new vehicle body type (nadwozie) — sync Google Sheet → body_types table → backend matchers → frontend chips.
---

# Add a new body type

## When to use

- User wants a new body type (e.g. "Podwozie Brygadowe Skrzynia", "Kombi Hi-Roof", "Pickup z zabudową").
- Existing body type's `utrata_wartosci` correction needs updating.

**Single Source of Truth: Google Sheet** (gid=484265370 — see memory `body_types_sot`). DB is downstream — never edit DB directly.

## Prerequisites

- Edit access to the SOT Google Sheet (`body_types` tab).
- Backend env with Poetry.
- `.env` configured for Supabase ONLINE.

## Steps

### 1. Add row in Google Sheet

- Open the body_types tab (SOT).
- Append: `name`, `utrata_wartosci` (decimal, e.g. `-0.01` for −1%), any other columns the sheet uses.
- Save.

### 2. Run sync to Supabase

```powershell
cd backend
poetry run python scripts/sync_body_types.py
```

This is a **KEEP** script — it's the legitimate ETL from Sheet → `body_types` table. Do NOT replace with a `fix_*.py`.

### 3. Verify DB state

```sql
-- via Supabase SQL Editor (READ ONLY query)
SELECT name, utrata_wartosci FROM body_types ORDER BY name;
```

The new row should be present.

### 4. Backend touchpoints (per [TABLE_REGISTRY.md](../../TABLE_REGISTRY.md))

`body_types` is read by:
- `backend/core/body_type_matcher.py` — string → body_type matching (extraction pipeline)
- `backend/core/samar_rv_fetchers.py` — pulls `utrata_wartosci` for WR Step-5 correction
- (no schema change needed unless new column)

If the new body type's name doesn't match what extraction returns, add an alias in `body_type_matcher.py` (look for the existing alias dict pattern).

### 5. Frontend touchpoint

- `frontend/src/BodyTypesCrud/BodyTypesCrudPanel.tsx` reads from `body_types`. Restart dev server — the new row appears automatically (no code change).
- If body type is used as a filter chip in ScoringSearch, it auto-populates from the universal features dictionary — no code change needed.

### 6. Two-way (round-trip) test

- Trigger an extraction (Vertex/Gemini) on a PDF that mentions this body type — verify `card_summary.body_type` matches new name.
- Run a calculation for a vehicle with this body type — verify the WR Step-5 correction is applied additively (see Golden Rule in CLAUDE.md) and the result shows in `LTRKalkulator` output.

## Verification

- DB row exists.
- `body_type_matcher` returns the new name for an expected input string.
- Calculation pipeline applies the correction additively to base catalogue price.
- Frontend chip / panel shows the new body type.

## Common pitfalls

- ❌ Editing `body_types` directly in Supabase SQL Editor. SOT is the Google Sheet — direct edits will be overwritten on next sync.
- ❌ Adding a body type only in backend matcher without the DB row → backend will reject extracted rows.
- ❌ Inventing a composite name from cabin+zabudowa AI signals. See memory `composite_body_style` — known anti-pattern.
- ❌ Multiplying WR by `(1 - utrata_wartosci)`. Correction is **additive on base catalogue net** — see CLAUDE.md Golden Rule.

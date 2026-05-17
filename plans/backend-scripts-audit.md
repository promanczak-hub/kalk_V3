# backend/scripts/ audit — Faza D1

**Status:** Draft. Categorization is based on filenames + ecosystem context (CLAUDE.md, TABLE_REGISTRY.md, memory). **DO NOT `git rm` anything without manual review.** Each `DELETE` candidate needs a 30-second look to confirm the work is truly done.

**Counts:** 70 scripts total.

| Category | Count | Action |
|---|---|---|
| KEEP | ~12 | Legitimate ongoing tooling (Sheets sync, audits, cache refresh). Add docstring header explaining when to run + how often. |
| MIGRATE | ~5 | Reframe as `.claude/skills/` (or a pytest fixture, or a CLI in a new `backend/tools/` package). |
| DELETE | ~37 | One-off `fix_*` / `repair_*` / `calc_X_debug` / vehicle-specific. Git history preserves them. |
| INVESTIGATE | ~16 | Unclear from name. Read the file (5 min each), reclassify. |

## KEEP (ongoing tooling)

These are real infra. Add a header docstring stating: purpose, when to run, frequency, dependencies.

| Script | Why keep |
|---|---|
| `audit_sheets.py` | Periodic SOT audit |
| `audit_sot_vs_db.py` | SOT vs DB drift detection |
| `check_tables.py` | DB structural sanity |
| `mdm_sync.py` | Master data sync |
| `refresh_all_caches.py` | Operational cache refresh |
| `sync_body_types.py` | SOT GSheet → `body_types` (referenced from `add-body-type` skill + CLAUDE.md) |
| `sync_control_center_gsheet.py` | GSheet → `control_center` (EAV) |
| `sync_depreciation_rates.py` | GSheet → `samar_class_depreciation_rates` |
| `sync_samar_classes.py` | GSheet → `samar_classes` |
| `sync_service_multipliers.py` | GSheet → `samar_class_service_rates` |
| `sync_ubezpieczenia_gsheet.py` | GSheet → `ltr_admin_ubezpieczenia` |
| `trigger_cross_reference.py` | Manual trigger for feature cross-reference job |

## MIGRATE (rewrite as skill or proper CLI)

| Script | Becomes |
|---|---|
| `diagnose_calculators.py` | `.claude/skills/diagnose-calculator-stage` (already written) |
| `diagnose_kalk_synthesis_link.py` | New skill — orphaned-vehicle-link diagnostic (related memory: `kalkulacja_vehicle_synthesis_link`) |
| `diagnose_and_refresh_all.py` | Split: diagnose part → skill; refresh part → `refresh_all_caches.py` (KEEP) |
| `verify_calc.py` | Part of `diagnose-calculator-stage` skill OR a `backend/tests/test_v1_parity_*` test |
| `calc_tavascan_debug.py` | Anti-pattern. Use `diagnose-calculator-stage` skill with vehicle_id arg |

## DELETE (one-off work, complete)

These were reactive fixes / one-time migrations / vehicle-specific debugging. Git history preserves them. Each delete needs ~30s confirmation that the underlying work is truly done.

```
add_insurance_params.py
analyze_excel_row.py
analyze_mcp_test_gsheet.py
backfill_discount.py
backfill_matrix_decomposition.py
backfill_model_trim.py
backfill_universal_features.py
calc_tavascan.py
calc_tavascan2.py
check_terramar.py
cleanup_passenger_cargo_params.py
dedupe_cechy_gsheet.py
enrich_gos.py
enrich_skody.py
find_v1_wr_terramar.py
fix_body_context.py
fix_google_sheet_names.py
fix_specjalny.py
fix_tab_okres_final.py
fix_validation_final.py
gen_okres_final_sql.py
import_tab_okres_final.py
investigate_kodiaq.py
map_drivetrain_to_suspension.py
migrate_tyre_costs.py
print_sheet_data.py
read_wr_klasa.py
recalibrate_service_from_lifetime_nonaso.py
revert_to_fks.py
revert_to_names.py
run_terramar_calc.py
script_kodiaq_test.py
sql_temp.py
test_refresh.py
update_cechy_columns.py
```

## INVESTIGATE (need 5 min read)

| Script | Why ambiguous |
|---|---|
| `process_csv_insurance.py` | Could be one-off import, or a regular ETL |
| `import_excel_twin.py` | Could be ongoing import tool or one-off |
| `extract_excel_coeff.py` | Possibly used by extraction pipeline tests |
| `cleanup_ghost_records.py` | Periodic cleanup or one-off? |
| `force_gsheet_validation.py` | Operational tool or hack? |
| `populate_rv_matrix_gsheet.py` | One-off populate or periodic? |
| `set_mdm_flags.py` | Periodic or one-off? |
| `set_semantic_powertrain_context.py` | Periodic backfill or one-off? |
| `setup_gsheet_contexts.py` | One-time setup script (likely DELETE) |
| `setup_gsheet_dictionaries.py` | One-time setup script (likely DELETE) |
| `test_supabase_conn.py` | Diagnostic tool — KEEP if it stays useful, else DELETE |
| `update_gsheet_rows.py` | Could be ongoing util |
| `update_sheet_models.py` | Could be ongoing util |
| `build_service_cost_resource.py` | Build artifact generator — could be CI step |
| `import_serwis_baza.py` | Periodic service base import? |
| `cleanup_user_overrides.py` | One-off cleanup or maintenance? |
| `repair_vehicle_metadata.py` | Recurring repair or one-off? Check usage logs |
| `revalidate_card_summary.py` | Useful periodic? Or part of `verify-extraction-output` skill? |

## Recommended execution order

1. **Step 1 — Confirm KEEP list.** Add docstring header to each. ~30 min.
2. **Step 2 — Process INVESTIGATE.** Open each file, decide. Move to KEEP/MIGRATE/DELETE. ~1.5 h.
3. **Step 3 — Migrate.** Move logic from MIGRATE scripts into skills or proper tests. ~3 h.
4. **Step 4 — Delete.** `git rm` the DELETE batch in one commit (`chore(scripts): remove one-off fix/repair/diagnose scripts`). Make user review the list first.

Before any `git rm`, confirm with the user. Don't make destructive changes in autonomous mode for this step — too many edge cases.

## Out of scope here

- Refactoring the KEEP scripts themselves (only adding docstring headers).
- Building a `backend/tools/` package as a proper CLI namespace. Worth doing later, but not in Faza D.

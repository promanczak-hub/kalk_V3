-- Deactivate the 13 naked duplicate equipment features.
--
-- Background: the catalog has historic pairs where a feature exists with two
-- keys (e.g. `abs` AND `eq_abs`) and both were flagged is_filterable=true.
-- The Reverse Search prompt then offered both to the LLM, which could match
-- both and inflate the score for a single concept.
--
-- vehicle_synthesis.feature_keys_present still contains the naked keys for
-- back-references (e.g. `abs` is in 57 vehicles, `eq_abs` also in 57 — same
-- vehicles). We do NOT touch feature_keys_present here — leaving naked keys
-- in there is harmless once they are not filterable.
--
-- Companion script: backend/scripts/dedupe_cechy_gsheet.py — must be run once
-- to mark Is_Filterable=FALSE in the SOT Google Sheet so that the next
-- mdm_sync.import_from_sheet() does not revert this change.

UPDATE reverse_search.universal_features uf
SET
  is_filterable = false,
  description = COALESCE(NULLIF(description, ''), '') ||
    CASE WHEN COALESCE(description, '') = '' THEN '' ELSE ' ' END ||
    '[DEPRECATED: duplicate of eq_' || uf.feature_key || ' — keep for vehicle_synthesis.feature_keys_present back-references but do not use as filter key]'
WHERE uf.is_active
  AND uf.is_filterable
  AND uf.feature_key IN (
    'abs',
    'aktywny_tempomat',
    'apple_car_play',
    'asr',
    'asystent_zmiany_pasa_ruchu',
    'czujniki_parkowania_tyl',
    'ekran_dotykowy',
    'esp',
    'felga_aluminiowa',
    'funkcja_szybkiego_ladowania_samochodu',
    'gps_nawigacja_satelitarna',
    'klimatyzacja_automatyczna',
    'klimatyzacja_dla_pasazerow_z_tylu'
  )
  AND EXISTS (
    SELECT 1 FROM reverse_search.universal_features eq
    WHERE eq.feature_key = 'eq_' || uf.feature_key
      AND eq.is_active
      AND eq.is_filterable
  );

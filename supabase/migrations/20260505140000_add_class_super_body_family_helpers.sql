-- Helpers for "apple-to-apple" gating of similar vehicles.
--
-- Today rpc_get_similar_vehicles_batch_semantic (20260504130000) ranks by
-- pure cosine distance and applies *no* categorical hard filter. That lets
-- absurd cross-segment hits leak through (e.g. Renault Master proposed for
-- Skoda Kodiaq) when the embedding happens to be close enough.
--
-- This migration only INTRODUCES the mapping helpers. It does NOT touch any
-- RPC — wiring them in as gates is a follow-up step so the mapping can be
-- audited against real data first.
--
-- Mappings are derived from:
--   - public.samar_classes (33 canonical SAMAR rows, see chunks.txt seed)
--   - parser_routes.classify_samar_category LLM single-tier labels
--   - core.body_type_matcher.BODY_ALIAS_MAP canonical body_style values
--
-- Both functions are IMMUTABLE so PostgreSQL can inline / index them.

-- ── fn_class_super ───────────────────────────────────────────────────────────
-- Maps any SAMAR category label (two-tier "Family - SIZE" or single-tier
-- "GRUPA ...") into one of:
--   'osobowy'   – passenger cars (sedan / hatchback / SUV / van-MPV / sport)
--   'dostawczy' – light & medium commercial, pickups, kombivans, furgonetki
--   'specjalny' – buses & minibuses (people-movers, not commercial cargo)
--   NULL        – unknown / "INNE" / unrecognised string
--
-- This is the COARSEST split. It is the single most important gate: if a
-- candidate's super-class differs from the source's, they should never be
-- presented as alternatives to each other regardless of embedding distance.

CREATE OR REPLACE FUNCTION public.fn_class_super(samar text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT CASE
        -- Two-tier samar_classes.name format ("Family - SIZE")
        WHEN samar ILIKE 'Podstawowa%'              THEN 'osobowy'
        WHEN samar ILIKE 'Sportowo-rekreacyjne%'    THEN 'osobowy'
        WHEN samar ILIKE 'Terenowo-rekreacyjne%'    THEN 'osobowy'
        WHEN samar ILIKE 'Vany%'                    THEN 'osobowy'
        WHEN samar ILIKE 'Lekkie dostawcze%'        THEN 'dostawczy'
        WHEN samar ILIKE '%dostawcze%'              THEN 'dostawczy'  -- Średnie / Ciężkie
        WHEN samar ILIKE 'Pick-up%'                 THEN 'dostawczy'
        WHEN samar ILIKE 'Kombivany%'               THEN 'dostawczy'
        WHEN samar ILIKE 'Furgon%'                  THEN 'dostawczy'
        WHEN samar ILIKE 'Autobusy%'                THEN 'specjalny'
        WHEN samar ILIKE 'Minibusy%'                THEN 'specjalny'
        -- Single-tier LLM labels (parser_routes.classify_samar_category)
        WHEN samar = 'GRUPA PODSTAWOWA'                 THEN 'osobowy'
        WHEN samar = 'SAMOCHODY SPORTOWO-REKREACYJNE'   THEN 'osobowy'
        WHEN samar = 'SAMOCHODY TERENOWO-REKREACYJNE'   THEN 'osobowy'
        WHEN samar = 'VANY'                             THEN 'osobowy'
        WHEN samar = 'KOMBIVANY'                        THEN 'dostawczy'
        WHEN samar = 'FURGONETKI'                       THEN 'dostawczy'
        WHEN samar = 'MINIBUSY'                         THEN 'specjalny'
        -- 'INNE' and anything we don't recognise → NULL (no gating possible)
        ELSE NULL
    END
$$;

COMMENT ON FUNCTION public.fn_class_super(text) IS
'Maps SAMAR category to a coarse super-class (osobowy/dostawczy/specjalny). '
'Used as the primary gate in similar-vehicles candidate selection. '
'Returns NULL for INNE/unknown so callers can decide whether to skip gating.';

-- ── fn_body_family ───────────────────────────────────────────────────────────
-- Maps a normalized body_style value (post BODY_ALIAS_MAP) into one of seven
-- families, used as a secondary gate. Looser than the current strict
-- `body_style = body_style` check — Sedan/Liftback collapse together,
-- Hatchback/Kombi collapse together, etc., so an Audi A5 Sportback can still
-- be proposed alongside a Sedan-bodied competitor without being filtered out.
--
-- Families:
--   'SUV'      – SUV (incl. Crossover via alias map)
--   'Hatch'    – Hatchback, Kombi (compact passenger, often shared platforms)
--   'Sedan'    – Sedan, Liftback
--   'Sport'    – Coupe, Cabrio, Roadster
--   'MPV'      – Minivan, Van, Wieloosobowy (passenger people-movers)
--   'Furgon'   – Furgon, Podwozie (commercial cargo body)
--   'Pickup'   – Pickup
--   NULL       – unknown / unmappable

CREATE OR REPLACE FUNCTION public.fn_body_family(body_style text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT CASE LOWER(COALESCE(body_style, ''))
        WHEN 'suv'           THEN 'SUV'
        WHEN 'crossover'     THEN 'SUV'
        WHEN 'hatchback'     THEN 'Hatch'
        WHEN 'kombi'         THEN 'Hatch'
        WHEN 'sedan'         THEN 'Sedan'
        WHEN 'liftback'      THEN 'Sedan'
        WHEN 'coupe'         THEN 'Sport'
        WHEN 'coupé'         THEN 'Sport'
        WHEN 'cabrio'        THEN 'Sport'
        WHEN 'cabriolet'     THEN 'Sport'
        WHEN 'roadster'      THEN 'Sport'
        WHEN 'minivan'       THEN 'MPV'
        WHEN 'van'           THEN 'MPV'
        WHEN 'wieloosobowy'  THEN 'MPV'
        WHEN 'furgon'        THEN 'Furgon'
        WHEN 'podwozie'      THEN 'Furgon'
        WHEN 'pickup'        THEN 'Pickup'
        WHEN 'pick-up'       THEN 'Pickup'
        ELSE NULL
    END
$$;

COMMENT ON FUNCTION public.fn_body_family(text) IS
'Coarse body family bucket (7 families). Looser than body_style equality so '
'Sedan/Liftback and Hatchback/Kombi cross-match. Returns NULL for unknown '
'inputs — callers decide fallback behaviour.';

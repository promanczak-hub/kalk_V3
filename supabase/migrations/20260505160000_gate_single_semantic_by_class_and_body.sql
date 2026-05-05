-- Same hard categorical gates as 20260505150000, but for the single-vehicle
-- semantic RPC. Uses fn_class_super / fn_body_family helpers from
-- 20260505140000. Mirrors the apple-to-apple gating used in batch semantic.
--
-- Without these gates a single-vehicle semantic lookup (called from
-- /scoring-search/vehicle/{id}/similar?mode=semantic) returns pure embedding
-- KNN — same Renault Master ↔ Skoda Kodiaq risk as the batch path before
-- 20260505150000.

CREATE OR REPLACE FUNCTION public.rpc_get_similar_vehicles_semantic(
    p_vehicle_id uuid,
    p_limit integer DEFAULT 4,
    p_duration_months integer DEFAULT NULL::integer,
    p_annual_mileage integer DEFAULT NULL::integer
)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_embedding vector(768);
  v_ref_samar text;
  v_ref_body  text;
BEGIN
  SELECT
    semantic_embedding,
    (synthesis_data->'mapped_ai_data'->>'samar_category')::text,
    COALESCE(
      (synthesis_data->'mapped_ai_data'->>'body_style')::text,
      (synthesis_data->'card_summary'->>'body_style')::text,
      (synthesis_data->'universal_features'->>'Rodzaj nadwozia')::text
    )
  INTO v_embedding, v_ref_samar, v_ref_body
  FROM vehicle_synthesis
  WHERE id = p_vehicle_id;

  IF v_embedding IS NULL THEN
    RETURN;
  END IF;

  RETURN QUERY
  SELECT
    jsonb_build_object(
      'vehicle_id', v.id,
      'brand', v.brand,
      'model', v.model,
      'version', COALESCE(v.synthesis_data->'card_summary'->>'trim_level', ''),
      'samar_category', COALESCE(v.synthesis_data->'card_summary'->>'samar_category', 'N/A'),
      'fuel', COALESCE(v.synthesis_data->'card_summary'->>'powertrain', 'N/A'),
      'transmission', COALESCE(v.synthesis_data->'card_summary'->>'transmission', 'N/A'),
      'image_url', COALESCE(v.synthesis_data->'card_summary'->>'image_url', ''),
      'similarity_score_pct', ROUND(((1 - (v.semantic_embedding <=> v_embedding)) * 100)::numeric, 2),
      'best_monthly_price', (
        SELECT MIN(monthly_price_net)
        FROM vehicle_matrix_cache mc
        WHERE mc.vehicle_id = v.id
        AND (p_duration_months IS NULL OR mc.duration_months = p_duration_months)
        AND (p_annual_mileage IS NULL OR mc.annual_mileage = p_annual_mileage)
      )
    )
  FROM vehicle_synthesis v
  WHERE v.id != p_vehicle_id
    AND v.semantic_embedding IS NOT NULL
    -- Source-side fail-open for both gates — matches batch semantic precedent.
    AND (
        public.fn_class_super(v_ref_samar) IS NULL
        OR public.fn_class_super(v_ref_samar) =
           public.fn_class_super(
               (v.synthesis_data->'mapped_ai_data'->>'samar_category')::text
           )
    )
    AND (
        public.fn_body_family(v_ref_body) IS NULL
        OR public.fn_body_family(v_ref_body) =
           public.fn_body_family(
               COALESCE(
                   (v.synthesis_data->'mapped_ai_data'->>'body_style')::text,
                   (v.synthesis_data->'card_summary'->>'body_style')::text,
                   (v.synthesis_data->'universal_features'->>'Rodzaj nadwozia')::text
               )
           )
    )
  ORDER BY v.semantic_embedding <=> v_embedding
  LIMIT p_limit;
END;
$function$;

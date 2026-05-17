/**
 * Value-For-Money score for the comparison-chart view.
 *
 * Formula: match_score_pct / (base_price_net / 1000)
 *   → points of "match" per 1 000 PLN of catalog price (net).
 *
 * Stable: depends only on the vehicle's own two fields — doesn't shift when
 * other vehicles enter or leave the result list.
 *
 * Returns null when the inputs are unusable (zero/missing price, missing
 * score). UI uses null to mean "hide on the VFM axis" rather than rendering
 * Infinity/NaN.
 */
export function computeVFM(
  matchScorePct: number | null | undefined,
  basePriceNet: number | null | undefined,
): number | null {
  if (matchScorePct == null) return null;
  if (basePriceNet == null || basePriceNet < 1000) return null;
  const ratio = matchScorePct / (basePriceNet / 1000);
  if (!Number.isFinite(ratio)) return null;
  return Math.round(ratio * 100) / 100;
}

/**
 * Human-friendly formatter for VFM. Empty string for null (so the UI can
 * collapse the badge instead of showing "—").
 */
export function formatVFM(vfm: number | null): string {
  if (vfm == null) return '';
  return vfm.toFixed(2);
}

import React from 'react';
import { Check } from 'lucide-react';

// ── Kalkulacja Params Row ───────────────────────────────────────────────────
// Renders the snapshot of toggles + financing knobs that produced the rate
// shown in the parent block. Wherever a price snapshot is shown in the app
// (search result card, similar-vehicles card, offer cart row), this component
// renders two compact lines beneath it:
//
//   "W cenie: ✓ Opony Premium · ✓ Ubezpieczenie · ✓ Auto zastępcze · ✓ Serwis ASO · Rabat 24%"
//   "Finansowanie: marża bankowa 2.2% · WIBOR 3.81%"
//
// Toggle semantics:
//   - `null/undefined` (unknown)     → hidden (no row added)
//   - `false` (explicitly disabled)  → strikethrough chip ("Auto zastępcze") so
//     the user can tell "off" from "n/a"
//   - `true`                         → green check chip
//
// All variants of the same `kalkulacja_id` share these values, so this row is
// keyed off the kalkulacja-level snapshot, not per matrix variant.

export interface KalkulacjaSnapshotShape {
  tire_class?: string | null;
  service_type?: string | null;
  discount_pct?: number | null;
  bank_margin_pct?: number | null;
  wibor_pct?: number | null;
  tires_included?: boolean | null;
  tire_buyback?: boolean | null;
  insurance_included?: boolean | null;
  replacement_car?: boolean | null;
  service_included?: boolean | null;
}

interface KalkulacjaParamsRowProps {
  snapshot: KalkulacjaSnapshotShape | null | undefined;
  /** Used when `snapshot.tire_class` is missing — typically the row's own
   *  tire_class column on `vehicle_matrix_cache`. */
  fallbackTireClass?: string | null;
  fallbackServiceType?: string | null;
  /** Used when no per-kalkulacja discount is present — typically the dealer
   *  discount % computed on the source offer (`car.applied_discount_pct`). */
  fallbackDiscountPct?: number | null;
  /** Optional override for the heading; defaults to "W cenie". Useful in the
   *  cart where space is tight and the heading can be omitted. */
  inclusiveHeading?: string;
  /** When true, drops the second-line "Finansowanie" row even if values are
   *  present. Used in the cart row where bank margin / WIBOR aren't relevant
   *  to the salesperson's decision. */
  hideFinancing?: boolean;
  /** Tighten everything to a single wrap-line. Used in narrow cart rows. */
  compact?: boolean;
}

const fmtPct = (v: number | null | undefined): string => {
  if (v == null) return '';
  return `${v.toFixed(v % 1 === 0 ? 0 : v < 10 ? 2 : 1)}%`;
};

const Toggle: React.FC<{ on: boolean | null | undefined; label: string }> = ({ on, label }) => {
  if (on == null) return null;
  return on ? (
    <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2 py-0.5">
      <Check className="w-3 h-3" /> {label}
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-slate-500 bg-slate-50 border border-slate-200 rounded-full px-2 py-0.5 line-through opacity-70">
      {label}
    </span>
  );
};

export const KalkulacjaParamsRow: React.FC<KalkulacjaParamsRowProps> = ({
  snapshot,
  fallbackTireClass,
  fallbackServiceType,
  fallbackDiscountPct,
  inclusiveHeading = 'W cenie',
  hideFinancing = false,
  compact = false,
}) => {
  const s = snapshot || {};
  const tireClass = s.tire_class ?? fallbackTireClass ?? null;
  const serviceType = s.service_type ?? fallbackServiceType ?? null;
  const discount = s.discount_pct ?? fallbackDiscountPct ?? null;
  const bankMargin = s.bank_margin_pct ?? null;
  const wibor = s.wibor_pct ?? null;

  const tiresLabel = tireClass ? `Opony ${tireClass}` : 'Opony';
  const serviceLabel = serviceType ? `Serwis ${serviceType}` : 'Serwis';

  const hasAnyToggle =
    s.tires_included != null ||
    s.insurance_included != null ||
    s.replacement_car != null ||
    s.service_included != null ||
    s.tire_buyback != null ||
    (discount != null && discount > 0);
  const hasFinancing = !hideFinancing && (bankMargin != null || wibor != null);

  if (!hasAnyToggle && !hasFinancing) return null;

  const rowGap = compact ? 'gap-1' : 'gap-1.5';

  return (
    <div className={`flex flex-col gap-1 text-[11px]`}>
      {hasAnyToggle && (
        <div className={`flex flex-wrap items-center ${rowGap}`}>
          {!compact && (
            <span className="text-[10px] uppercase tracking-wider text-slate-600 font-semibold mr-0.5">
              {inclusiveHeading}
            </span>
          )}
          <Toggle on={s.tires_included} label={tiresLabel} />
          <Toggle on={s.tire_buyback} label="Odkup opon" />
          <Toggle on={s.insurance_included} label="Ubezpieczenie" />
          <Toggle on={s.replacement_car} label="Auto zastępcze" />
          <Toggle on={s.service_included} label={serviceLabel} />
          {discount != null && discount > 0 && (
            <span className="inline-flex items-center gap-1 text-violet-700 bg-violet-50 border border-violet-200 rounded-full px-2 py-0.5 font-mono tabular-nums">
              Rabat {fmtPct(discount)}
            </span>
          )}
        </div>
      )}
      {hasFinancing && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-slate-600">
          <span className="text-[10px] uppercase tracking-wider text-slate-600 font-semibold">
            Finansowanie
          </span>
          {bankMargin != null && (
            <span className="font-mono tabular-nums" title="Marża banku zaszyta w racie">
              marża bankowa <strong className="text-slate-800">{fmtPct(bankMargin)}</strong>
            </span>
          )}
          {wibor != null && (
            <span className="font-mono tabular-nums" title="Stawka WIBOR użyta w kalkulacji">
              WIBOR <strong className="text-slate-800">{fmtPct(wibor)}</strong>
            </span>
          )}
        </div>
      )}
    </div>
  );
};

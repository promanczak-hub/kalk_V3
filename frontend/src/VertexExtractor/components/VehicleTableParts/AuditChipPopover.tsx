import { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import { ScanSearch, CheckCircle2, AlertTriangle, Lock, ChevronDown } from "lucide-react";
import type { DiscountBreakdown, PriceValidation } from "../../types";
import { DiscountAuditCard } from "./DiscountAuditCard";
import { PriceAuditCard } from "./PriceAuditCard";

interface AuditChipPopoverProps {
  vehicleId: string;
  // Discount audit
  discount: DiscountBreakdown | null | undefined;
  priceValidation?: PriceValidation | null;
  activeMode: "offer" | "suggested" | "custom";
  activeDiscountPct: number;
  activeDiscountAmountNet: number;
  discountableBaseNet: number;
  nonDiscountableTotalNet: number;
  // Price audit
  cardSummary: Record<string, unknown> | null | undefined;
  catalogBasePriceNet: number;
  discountableOptionsNet: number;
  nonDiscountableOptionsNet: number;
  serviceTotalNet: number;
  onUpdated?: () => void;
}

/**
 * Compact status chip (placed next to SUMA CAŁKOWITA) that opens a popover
 * combining the discount audit + price audit into one block — instead of two
 * full-width cards in the row body.
 *
 * The popover is rendered in a PORTAL with `position: fixed` anchored to the
 * chip, because the row card uses `overflow-hidden` (for rounded corners +
 * expand animation) which otherwise clips the popover to the collapsed header.
 */
const POP_W = 460;

export function AuditChipPopover(props: AuditChipPopoverProps) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const chipRef = useRef<HTMLButtonElement>(null);
  const popRef = useRef<HTMLDivElement>(null);

  const computePos = useCallback(() => {
    const r = chipRef.current?.getBoundingClientRect();
    if (!r) return;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    // Align popover's right edge with the chip, clamped into the viewport.
    let left = Math.min(r.right - POP_W, vw - POP_W - 8);
    left = Math.max(8, left);
    // Open downward; flip up if not enough room below.
    const estH = Math.min(vh * 0.72, 620);
    let top = r.bottom + 6;
    if (top + estH > vh - 8) {
      const above = r.top - estH - 6;
      top = above > 8 ? above : Math.max(8, vh - estH - 8);
    }
    setPos({ top, left });
  }, []);

  useEffect(() => {
    if (!open) return;
    computePos();
    const onScroll = () => computePos();
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node;
      if (chipRef.current?.contains(t) || popRef.current?.contains(t)) return;
      setOpen(false);
    };
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    // capture=true so nested scroll containers (the vehicle list) reposition too
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onScroll);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onEsc);
    return () => {
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onScroll);
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open, computePos]);

  const warnings = props.priceValidation?.warnings || [];
  const hasError = warnings.some((w) => w.severity === "ERROR");
  const hasWarn = warnings.some((w) => w.severity === "WARNING");
  const confirmed =
    (props.cardSummary as Record<string, unknown> | null | undefined)?._price_confirmed === true;

  const tone = confirmed
    ? "bg-emerald-50 border-emerald-300 text-emerald-700 hover:bg-emerald-100"
    : hasError
      ? "bg-red-50 border-red-300 text-red-700 hover:bg-red-100"
      : hasWarn
        ? "bg-amber-50 border-amber-300 text-amber-700 hover:bg-amber-100"
        : "bg-slate-50 border-slate-300 text-slate-600 hover:bg-slate-100";
  const StatusIcon = confirmed ? Lock : hasError || hasWarn ? AlertTriangle : CheckCircle2;

  return (
    // stopPropagation: chip lives inside the row header (onClick toggles expand)
    <div className="inline-block" onClick={(e) => e.stopPropagation()}>
      <button
        ref={chipRef}
        type="button"
        onClick={() => setOpen((o) => !o)}
        title="Audyt rabatu i ceny"
        className={`inline-flex items-center gap-1 border px-2 py-0.5 h-[22px] rounded text-[10px] font-semibold transition-colors cursor-pointer shadow-sm ${tone}`}
      >
        <ScanSearch className="w-3 h-3" />
        Audyt
        {props.activeDiscountPct > 0 && (
          <span className="font-mono">· {props.activeDiscountPct.toFixed(1)}%</span>
        )}
        <StatusIcon className="w-3 h-3" />
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open &&
        pos &&
        createPortal(
          <div
            ref={popRef}
            onClick={(e) => e.stopPropagation()}
            style={{
              position: "fixed",
              top: pos.top,
              left: pos.left,
              width: POP_W,
              maxWidth: "92vw",
              zIndex: 1000,
            }}
            className="max-h-[72vh] overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-xl p-3 space-y-3 text-left cursor-default animate-in fade-in slide-in-from-top-1 duration-150"
          >
            <DiscountAuditCard
              vehicleId={props.vehicleId}
              discount={props.discount}
              priceValidation={props.priceValidation}
              activeMode={props.activeMode}
              activeDiscountPct={props.activeDiscountPct}
              activeDiscountAmountNet={props.activeDiscountAmountNet}
              discountableBaseNet={props.discountableBaseNet}
              nonDiscountableTotalNet={props.nonDiscountableTotalNet}
              onUpdated={props.onUpdated}
              defaultExpanded
            />
            <PriceAuditCard
              vehicleId={props.vehicleId}
              cardSummary={props.cardSummary}
              priceValidation={props.priceValidation}
              catalogBasePriceNet={props.catalogBasePriceNet}
              discountableOptionsNet={props.discountableOptionsNet}
              nonDiscountableOptionsNet={props.nonDiscountableOptionsNet}
              serviceTotalNet={props.serviceTotalNet}
              activeDiscountAmountNet={props.activeDiscountAmountNet}
              onUpdated={props.onUpdated}
              defaultExpanded
            />
          </div>,
          document.body,
        )}
    </div>
  );
}

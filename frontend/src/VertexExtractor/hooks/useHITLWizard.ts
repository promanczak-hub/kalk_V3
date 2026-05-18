import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiClient } from "../../lib/apiClient";
import { supabase } from "../../lib/supabaseClient";
import type {
  ApplyResponse,
  BucketId,
  CabinKind,
  DiscountDraft,
  ItemDraft,
  PreviewResponse,
  PriceType,
  ZabudowaSotKey,
} from "../components/HITLWizard/types";
import { DUPLICATE_KEYWORDS } from "../components/HITLWizard/types";

interface VehicleSynthesisRow {
  id: string;
  brand?: string;
  model?: string;
  verification_status?: string;
  synthesis_data?: {
    card_summary?: {
      paid_options?: PaidOptionRow[];
      service_equipment?: {
        components?: ServiceComponentRow[];
      };
      base_price?: string;
      body_style?: string;
      _price_domain?: string;
      hallucinated_fields?: string[];
    };
  };
}

interface PaidOptionRow {
  field_id?: string;
  name: string;
  price?: string;
  price_type?: string;
  category?: string;
  confidence?: number;
}

interface ServiceComponentRow {
  field_id?: string;
  name: string;
  price_net?: string;
  price_gross?: string;
  confidence?: number;
}

function parsePriceString(s: string | undefined | null): {
  value: number;
  type: PriceType;
} {
  if (!s) return { value: 0, type: "brutto" };
  const cleaned = s.replace(/\s+/g, "").replace(",", ".");
  const numMatch = cleaned.match(/[-+]?\d+(\.\d+)?/);
  const value = numMatch ? parseFloat(numMatch[0]) : 0;
  const type: PriceType = /netto/i.test(s) ? "netto" : "brutto";
  return { value, type };
}

function hasDuplicateKeyword(name: string): boolean {
  const lower = name.toLowerCase();
  return DUPLICATE_KEYWORDS.some((k) => lower.includes(k));
}

function buildItemDrafts(row: VehicleSynthesisRow): ItemDraft[] {
  const cs = row.synthesis_data?.card_summary || {};
  const items: ItemDraft[] = [];
  const counters: Record<string, number> = {};

  // paid_options
  (cs.paid_options || []).forEach((opt, idx) => {
    const fid =
      opt.field_id || `paid-${idx}-${(counters.po = (counters.po || 0) + 1)}`;
    const { value, type } = parsePriceString(opt.price);
    items.push({
      field_id: fid,
      name: opt.name || "(brak nazwy)",
      price_value: value,
      price_type: (opt.price_type as PriceType) || type,
      vat_rate: 0.23,
      category: opt.category || "",
      confidence: opt.confidence ?? 1.0,
      source_section: `paid_options[${idx}]`,
      bucket: "factory",
      is_duplicate_candidate: hasDuplicateKeyword(opt.name || ""),
    });
  });

  // service_equipment.components
  const components = cs.service_equipment?.components || [];
  components.forEach((comp, idx) => {
    const fid =
      comp.field_id ||
      `comp-${idx}-${(counters.comp = (counters.comp || 0) + 1)}`;
    const grossStr = comp.price_gross || "0";
    const grossMatch = grossStr.replace(/\s+/g, "").match(/[-+]?\d+(\.\d+)?/);
    const grossValue = grossMatch ? parseFloat(grossMatch[0]) : 0;
    items.push({
      field_id: fid,
      name: comp.name || "(brak nazwy)",
      price_value: grossValue,
      price_type: "brutto",
      vat_rate: 0.23,
      category: "Zabudowa",
      confidence: comp.confidence ?? 1.0,
      source_section: `service_equipment.components[${idx}]`,
      bucket: "zabudowa",
      is_duplicate_candidate: hasDuplicateKeyword(comp.name || ""),
    });
  });

  // Sort by confidence ASC (najmniej pewne na górze)
  items.sort((a, b) => a.confidence - b.confidence);
  return items;
}

const DEFAULT_DISCOUNT: DiscountDraft = {
  rabat_type: "kwotowo",
  rabat_basis: "brutto",
  rabat_value: 0,
  discount_scope: ["base", "factory_options"],
};

export function useHITLWizard() {
  const [isOpen, setIsOpen] = useState(false);
  const [vehicle, setVehicle] = useState<VehicleSynthesisRow | null>(null);
  const [items, setItems] = useState<ItemDraft[]>([]);
  const [cabinKind, setCabinKind] = useState<CabinKind | null>(null);
  const [zabudowaSotKey, setZabudowaSotKey] = useState<ZabudowaSotKey | null>(null);
  const [discount, setDiscount] = useState<DiscountDraft>(DEFAULT_DISCOUNT);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const previewDebounceRef = useRef<number | null>(null);

  const openForVehicle = useCallback((row: VehicleSynthesisRow) => {
    setVehicle(row);
    setItems(buildItemDrafts(row));
    // Initial cabin/zabudowa best-guess from body_style
    const body = row.synthesis_data?.card_summary?.body_style || "";
    const lower = body.toLowerCase();
    if (lower.includes("furgon") && lower.includes("brygad")) {
      setCabinKind("furgon_brygadowy");
    } else if (lower.includes("furgon")) {
      setCabinKind("furgon");
    } else if (lower.includes("podwozie") && lower.includes("brygad")) {
      setCabinKind("podwozie_brygadowe");
    } else if (lower.includes("podwozie")) {
      setCabinKind("podwozie");
    }
    setZabudowaSotKey(null);
    setDiscount(DEFAULT_DISCOUNT);
    setPreview(null);
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    setVehicle(null);
    setItems([]);
    setPreview(null);
  }, []);

  const moveItem = useCallback((field_id: string, bucket: BucketId) => {
    setItems((prev) =>
      prev.map((it) => (it.field_id === field_id ? { ...it, bucket } : it))
    );
  }, []);

  const updatePrice = useCallback((field_id: string, value: number) => {
    setItems((prev) =>
      prev.map((it) =>
        it.field_id === field_id ? { ...it, price_value: value } : it
      )
    );
  }, []);

  const updatePriceType = useCallback((field_id: string, type: PriceType) => {
    setItems((prev) =>
      prev.map((it) => (it.field_id === field_id ? { ...it, price_type: type } : it))
    );
  }, []);

  const updateVatRate = useCallback((field_id: string, rate: number) => {
    setItems((prev) =>
      prev.map((it) => (it.field_id === field_id ? { ...it, vat_rate: rate } : it))
    );
  }, []);

  const buildPayload = useCallback(() => {
    return {
      cabin_kind: cabinKind,
      zabudowa_sot_key: zabudowaSotKey,
      price_corrections: items.map((it) => ({
        field_id: it.field_id,
        bucket: it.bucket,
        price_value: it.price_value,
        price_type: it.price_type,
        vat_rate: it.vat_rate,
      })),
      discount: discount.rabat_value > 0 || discount.discount_scope.length > 0
        ? discount
        : null,
    };
  }, [cabinKind, zabudowaSotKey, items, discount]);

  // Debounced preview fetch on every meaningful change
  useEffect(() => {
    if (!isOpen || !vehicle) return;
    if (previewDebounceRef.current !== null) {
      window.clearTimeout(previewDebounceRef.current);
    }
    setPreviewLoading(true);
    previewDebounceRef.current = window.setTimeout(async () => {
      try {
        const res = await apiClient.post<PreviewResponse>(
          `/api/extract/hitl/preview/${vehicle.id}`,
          buildPayload(),
          { skipGlobalError: true }
        );
        setPreview(res);
        setPreviewError(null);
      } catch (e) {
        const msg = e instanceof Error ? e.message : "preview fetch failed";
        setPreviewError(msg);
      } finally {
        setPreviewLoading(false);
      }
    }, 400);
    return () => {
      if (previewDebounceRef.current !== null) {
        window.clearTimeout(previewDebounceRef.current);
      }
    };
  }, [isOpen, vehicle, buildPayload]);

  const save = useCallback(
    async (userNotes?: string): Promise<ApplyResponse | null> => {
      if (!vehicle) return null;
      setIsSaving(true);
      try {
        const res = await apiClient.post<ApplyResponse>(
          `/api/extract/hitl/apply/${vehicle.id}`,
          { ...buildPayload(), user_notes: userNotes || "" }
        );
        close();
        return res;
      } finally {
        setIsSaving(false);
      }
    },
    [vehicle, buildPayload, close]
  );

  const bucketTotals = useMemo(() => {
    const totals = { base: 0, factory: 0, zabudowa: 0, agregat: 0 };
    items.forEach((it) => {
      if (it.bucket === "skip" || !(it.bucket in totals)) return;
      const gross =
        it.price_type === "brutto"
          ? it.price_value
          : it.price_value * (1 + it.vat_rate);
      totals[it.bucket as keyof typeof totals] += gross;
    });
    return totals;
  }, [items]);

  // Supabase Realtime: auto-open wizard when vehicle status flips to needs_review
  useEffect(() => {
    const channel = supabase
      .channel("hitl_wizard_realtime")
      .on(
        "postgres_changes",
        { event: "UPDATE", schema: "public", table: "vehicle_synthesis" },
        (payload) => {
          const newRow = payload.new as VehicleSynthesisRow;
          const oldRow = payload.old as VehicleSynthesisRow;
          if (
            newRow.verification_status === "needs_review" &&
            oldRow?.verification_status !== "needs_review" &&
            !isOpen
          ) {
            // Auto-open
            openForVehicle(newRow);
          }
        }
      )
      .subscribe();
    return () => {
      supabase.removeChannel(channel);
    };
  }, [isOpen, openForVehicle]);

  return {
    isOpen,
    vehicle,
    items,
    cabinKind,
    setCabinKind,
    zabudowaSotKey,
    setZabudowaSotKey,
    discount,
    setDiscount,
    preview,
    previewLoading,
    previewError,
    isSaving,
    bucketTotals,
    openForVehicle,
    close,
    moveItem,
    updatePrice,
    updatePriceType,
    updateVatRate,
    save,
  };
}

import { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Calculator,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Sparkles,
  Lock,
  Loader2,
  Pencil,
  X,
} from "lucide-react";
import type { PriceValidation, PriceDeduction, DeducedOption, PriceReconciliation, DiscountBreakdown } from "../../types";
import { apiClient } from "../../../lib/apiClient";
import { parsePriceToNumber } from "./PriceDualFormat";
import { revalidateVehicleQuiet } from "../../hooks/useRevalidateVehicle";
import { PriceReconciliationPanel } from "./PriceReconciliationPanel";

const VAT = 1.23;

interface PriceAuditCardProps {
  vehicleId: string;
  cardSummary: Record<string, unknown> | null | undefined;
  priceValidation?: PriceValidation | null;
  catalogBasePriceNet: number;
  discountableOptionsNet: number;
  nonDiscountableOptionsNet: number;
  serviceTotalNet: number;
  onUpdated?: () => void;
  defaultExpanded?: boolean;
}

type Domain = "netto" | "brutto";

const fmtPln = (v: number | null | undefined): string => {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${v.toLocaleString("pl-PL", { maximumFractionDigits: 0 })} zł`;
};

const round2 = (v: number): number => Math.round(v * 100) / 100;

const parseInputNumber = (s: string): number | null => {
  if (!s.trim()) return null;
  const cleaned = s.replace(/\s/g, "").replace(",", ".");
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
};

const readNum = (obj: Record<string, unknown> | null | undefined, key: string): number | null => {
  const v = obj?.[key];
  return typeof v === "number" && Number.isFinite(v) ? v : null;
};

/** Net + gross pair, filling the missing side via VAT when only one is known. */
const pair = (net: number | null, gross: number | null): { net: number | null; gross: number | null } => {
  if (net !== null && gross !== null) return { net, gross };
  if (net !== null) return { net, gross: round2(net * VAT) };
  if (gross !== null) return { net: round2(gross / VAT), gross };
  return { net: null, gross: null };
};

function Badge({ tone, children }: { tone: "emerald" | "amber" | "red" | "slate"; children: React.ReactNode }) {
  const map = {
    emerald: "bg-emerald-100 text-emerald-700",
    amber: "bg-amber-100 text-amber-700",
    red: "bg-red-100 text-red-700",
    slate: "bg-slate-100 text-slate-600",
  };
  return <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${map[tone]}`}>{children}</span>;
}

function PriceRow({
  label,
  net,
  gross,
  hint,
  deduced,
  bold,
  sign,
}: {
  label: string;
  net: number | null;
  gross: number | null;
  hint?: string;
  deduced?: boolean;
  bold?: boolean;
  sign?: "+" | "−";
}) {
  return (
    <div className="flex items-center justify-between gap-3 py-1 border-b border-slate-100 last:border-b-0">
      <div className="flex items-center gap-1 text-[11px] text-slate-500 min-w-0">
        {sign && <span className="text-slate-400 font-mono">{sign}</span>}
        <span className="truncate">{label}</span>
        {hint && (
          <span title={hint}>
            <HelpCircle className="w-3 h-3 text-slate-400 flex-shrink-0" />
          </span>
        )}
        {deduced && <Badge tone="amber">wydedukowane</Badge>}
      </div>
      <div className="flex items-center gap-3 font-mono flex-shrink-0">
        <span className={`text-xs ${bold ? "font-bold text-slate-900" : "font-medium text-slate-600"}`}>{fmtPln(net)}<span className="text-[9px] text-slate-400 ml-0.5">netto</span></span>
        <span className={`text-xs ${bold ? "font-bold text-slate-700" : "text-slate-400"}`}>{fmtPln(gross)}<span className="text-[9px] text-slate-400 ml-0.5">brutto</span></span>
      </div>
    </div>
  );
}

const BUCKET_LABEL: Record<DeducedOption["bucket"], string> = {
  katalogowa: "Katalogowa",
  fabryczna: "Fabryczna",
  serwisowa: "Serwisowa",
};

export function PriceAuditCard({
  vehicleId,
  cardSummary,
  priceValidation,
  catalogBasePriceNet,
  discountableOptionsNet,
  nonDiscountableOptionsNet,
  serviceTotalNet,
  onUpdated,
  defaultExpanded = false,
}: PriceAuditCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [deducing, setDeducing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [deduction, setDeduction] = useState<PriceDeduction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reconciling, setReconciling] = useState(false);
  const [reconciliation, setReconciliation] = useState<PriceReconciliation | null>(() => {
    const rec = (cardSummary as Record<string, unknown> | null | undefined)?._reconciliation;
    return rec && typeof rec === "object" ? (rec as PriceReconciliation) : null;
  });

  const cs = cardSummary || {};
  const domain = String((cs as Record<string, unknown>)._price_domain || (cs as Record<string, unknown>).price_domain || "unknown");
  const isConfirmed = (cs as Record<string, unknown>)._price_confirmed === true;

  // ── Provenance: was base derived rather than read from the PDF? ──
  const baseDerived =
    (cs as Record<string, unknown>)._base_derived === true ||
    (priceValidation?.warnings || []).some(
      (w) => w.rule === "BASE_AUTO_DERIVED" || w.rule === "AUTO_FIX_APPLIED",
    );

  // ── Extraction total (net), for the consistency check ──
  const strToNet = (s: unknown): number | null => {
    if (typeof s !== "string" || !s.trim()) return null;
    const raw = parsePriceToNumber(s);
    if (!(raw > 0)) return null;
    const low = s.toLowerCase();
    const isGross = low.includes("brutto") || (domain === "brutto" && !low.includes("netto"));
    return isGross ? round2(raw / VAT) : raw;
  };
  const extractedTotalNet =
    readNum(cs as Record<string, unknown>, "total_price_net") ?? strToNet((cs as Record<string, unknown>).total_price);

  // ── Live breakdown (what the calculator currently uses), unless overridden by LLM ──
  const liveBase = pair(deduction ? deduction.base_net : catalogBasePriceNet, deduction ? deduction.base_gross : null);
  const liveDiscOpt = pair(deduction ? deduction.discountable_options_net : discountableOptionsNet, deduction ? deduction.discountable_options_gross : null);
  const liveNonDiscOpt = pair(deduction ? deduction.non_discountable_options_net : nonDiscountableOptionsNet, deduction ? deduction.non_discountable_options_gross : null);
  const liveService = pair(deduction ? deduction.service_net : serviceTotalNet, deduction ? deduction.service_gross : null);

  // PDF-grounded rabat ONLY. The active discount (offer / suggested-from-DB / custom)
  // is the calculator's overlay and lives in DiscountAuditCard — it must never be mixed
  // into the price audit, which validates strictly what the PDF prints.
  const pdfDiscount = (cs as Record<string, unknown>).discount as DiscountBreakdown | undefined;
  const pdfRabatNet = (() => {
    if (!pdfDiscount || pdfDiscount.extraction_method === "none") return 0;
    if (typeof pdfDiscount.explicit_rabat_pln === "number" && pdfDiscount.explicit_rabat_pln > 0) {
      return pdfDiscount.explicit_rabat_pln;
    }
    const pct = pdfDiscount.computed_pct ?? pdfDiscount.explicit_rabat_pct;
    const base = pdfDiscount.discountable_base_net ?? catalogBasePriceNet + discountableOptionsNet;
    return typeof pct === "number" && pct > 0 && base > 0 ? round2(base * (pct / 100)) : 0;
  })();
  const rabatNet = deduction ? deduction.rabat_pln : pdfRabatNet;

  const computedTotalNet =
    (liveBase.net ?? 0) + (liveDiscOpt.net ?? 0) + (liveNonDiscOpt.net ?? 0) + (liveService.net ?? 0) - (rabatNet || 0);
  const computedTotalGross = round2(computedTotalNet * VAT);

  // ── Reconciliation verdict ──
  const targetTotalNet = deduction ? deduction.total_net : extractedTotalNet;
  let verdict: "ok" | "mismatch" | "incomplete";
  let delta = 0;
  if (targetTotalNet === null || targetTotalNet === undefined) {
    verdict = "incomplete";
  } else {
    delta = computedTotalNet - targetTotalNet;
    const tol = Math.max(2, targetTotalNet * 0.005);
    verdict = Math.abs(delta) <= tol ? "ok" : "mismatch";
  }

  const verdictCfg = {
    ok: { tone: "emerald" as const, icon: CheckCircle2, label: "spójne" },
    mismatch: { tone: "red" as const, icon: AlertTriangle, label: "niespójne" },
    incomplete: { tone: "amber" as const, icon: AlertTriangle, label: "niekompletne" },
  }[verdict];
  const VIcon = verdictCfg.icon;

  const handleDeduce = async (known?: Record<string, number | null>) => {
    setDeducing(true);
    setError(null);
    try {
      const body = known
        ? Object.fromEntries(Object.entries(known).filter(([, v]) => v !== null && v !== undefined))
        : {};
      const res = await apiClient.fetch(`/api/extract/price-deduce/${vehicleId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setDeduction(data.deduction as PriceDeduction);
      setShowForm(false);
    } catch (e) {
      console.error(e);
      setError("Dedukcja LLM nieudana — spróbuj ponownie lub wpisz ceny cząstkowe ręcznie.");
    } finally {
      setDeducing(false);
    }
  };

  const handleReconcile = async () => {
    setReconciling(true);
    setError(null);
    try {
      const res = await apiClient.fetch(`/api/extract/price-reconcile/${vehicleId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setReconciliation(data.reconciliation as PriceReconciliation);
    } catch (e) {
      console.error(e);
      setError("Audyt 4 ścieżek nieudany — spróbuj ponownie.");
    } finally {
      setReconciling(false);
    }
  };

  const handleConfirm = async () => {
    setConfirming(true);
    setError(null);
    try {
      // no_discount flags apply to paid_options (factory items only).
      const flags = (deduction?.options || [])
        .filter((o) => o.field_id && o.bucket !== "serwisowa")
        .map((o) => ({ field_id: o.field_id as string, no_discount: !o.discountable }));
      // Correct factory paid_options net/gross so per-line prices match totals.
      const factoryOptions = (deduction?.options || [])
        .filter((o) => o.bucket === "fabryczna")
        .map((o) => ({
          field_id: o.field_id || "",
          name: o.name,
          net: o.net,
          gross: o.gross,
          no_discount: !o.discountable,
        }));
      // Service/zabudowa components → service_equipment split (Agregat + Kontener).
      const serviceComponents = (deduction?.options || [])
        .filter((o) => o.bucket === "serwisowa" && o.net > 0)
        .map((o) => ({ name: o.name, net: o.net, gross: o.gross }));
      const serviceName =
        (cs as Record<string, unknown>)?.service_equipment &&
        ((cs as Record<string, Record<string, unknown>>).service_equipment?.name as string | undefined);
      const res = await apiClient.fetch(`/api/extract/price-confirm/${vehicleId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          domain: "netto",
          base_net: liveBase.net ?? 0,
          discountable_options_net: liveDiscOpt.net ?? 0,
          non_discountable_options_net: liveNonDiscOpt.net ?? 0,
          service_net: liveService.net ?? 0,
          total_net: targetTotalNet ?? computedTotalNet,
          rabat_pln: rabatNet || 0,
          option_discount_flags: flags,
          factory_options: factoryOptions,
          service_name: serviceName || undefined,
          service_components: serviceComponents,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      await revalidateVehicleQuiet(vehicleId);
      onUpdated?.();
    } catch (e) {
      console.error(e);
      setError("Nie udało się zatwierdzić ceny — sprawdź konsolę.");
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className={`rounded-lg border ${verdict === "ok" ? "border-emerald-200 bg-emerald-50/30" : verdict === "mismatch" ? "border-red-200 bg-red-50/20" : "border-amber-200 bg-amber-50/20"}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-slate-50/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Calculator className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-semibold text-slate-700">Audyt ceny</span>
          <Badge tone={verdictCfg.tone}>
            <VIcon className="w-3 h-3" />
            {verdictCfg.label}
          </Badge>
          {isConfirmed && (
            <Badge tone="emerald">
              <Lock className="w-3 h-3" />
              zatwierdzone
            </Badge>
          )}
          {deduction && (
            <Badge tone="slate">
              <Sparkles className="w-3 h-3" />
              dedukcja LLM
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="font-mono font-bold text-slate-800">{fmtPln(computedTotalGross)} brutto</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-3 border-t border-current/5">
          {/* ── Audyt 4 ścieżek (reconciliation) ── */}
          <PriceReconciliationPanel
            reconciliation={reconciliation}
            loading={reconciling}
            onRun={handleReconcile}
          />

          {/* ── Rozkład ceny ── */}
          <section>
            <h6 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 mt-2">
              Rozkład ceny {deduction ? "(z dedukcji LLM)" : "(z ekstrakcji)"}
            </h6>
            <PriceRow label="Baza katalogowa" net={liveBase.net} gross={liveBase.gross} deduced={baseDerived || deduction?.deduced_fields.includes("base_net")} bold />
            {deduction ? (
              <>
                <PriceRow label="Opcje fabryczne (rabatowane)" net={liveDiscOpt.net} gross={liveDiscOpt.gross} sign="+" />
                <PriceRow label="Opcje fabryczne (nierabatowane)" net={liveNonDiscOpt.net} gross={liveNonDiscOpt.gross} sign="+" hint="W niektórych markach część opcji fabrycznych nie podlega rabatowi" />
              </>
            ) : (
              <PriceRow label="Opcje fabryczne (Σ)" net={(liveDiscOpt.net ?? 0) + (liveNonDiscOpt.net ?? 0)} gross={round2(((liveDiscOpt.net ?? 0) + (liveNonDiscOpt.net ?? 0)) * VAT)} sign="+" />
            )}
            <PriceRow label="Zabudowa / serwis (nierabatowane)" net={liveService.net} gross={liveService.gross} sign="+" hint="Pakiety serwisowe / zabudowa — zawsze poza rabatem" />
            <PriceRow label="Rabat (z PDF)" net={rabatNet ? -rabatNet : 0} gross={rabatNet ? round2(-rabatNet * VAT) : 0} sign="−" />
            <PriceRow label="Total (wyliczony)" net={computedTotalNet} gross={computedTotalGross} bold />
          </section>

          {/* ── Równanie spójności ── */}
          <section className="pt-2 border-t border-slate-100">
            <div className={`text-[11px] rounded px-2 py-1.5 border ${verdict === "ok" ? "bg-emerald-50 border-emerald-200 text-emerald-800" : verdict === "mismatch" ? "bg-red-50 border-red-200 text-red-800" : "bg-amber-50 border-amber-200 text-amber-800"}`}>
              <div className="flex items-center gap-1.5 font-semibold">
                <VIcon className="w-3.5 h-3.5" />
                {verdict === "ok" && "Suma komponentów zgadza się z total z ekstrakcji."}
                {verdict === "mismatch" && `Niezgodność: wyliczony total ${fmtPln(computedTotalNet)} ≠ total z ekstrakcji ${fmtPln(targetTotalNet)} (Δ ${fmtPln(delta)}).`}
                {verdict === "incomplete" && "Brak pełnego total z ekstrakcji — uruchom dedukcję LLM lub wpisz ceny cząstkowe."}
              </div>
              <p className="mt-0.5 font-mono text-[10px] opacity-70">
                baza + opcje + zabudowa − rabat = total
              </p>
            </div>
          </section>

          {/* ── Klasyfikacja opcji (po dedukcji) ── */}
          {deduction && deduction.options.length > 0 && (
            <section className="pt-2 border-t border-slate-100">
              <h6 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                Klasyfikacja opcji
              </h6>
              <div className="space-y-1">
                {deduction.options.map((o, i) => (
                  <div key={i} className="flex items-center justify-between gap-2 text-[11px] py-0.5">
                    <span className="truncate text-slate-600">{o.name}</span>
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <Badge tone="slate">{BUCKET_LABEL[o.bucket]}</Badge>
                      <Badge tone={o.discountable ? "emerald" : "red"}>
                        {o.discountable ? "rabatowana" : "nierabatowana"}
                      </Badge>
                      <span className="font-mono text-slate-500">{fmtPln(o.net)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* ── Uzasadnienie LLM ── */}
          {deduction && deduction.reasoning && (
            <section className="pt-2 border-t border-slate-100">
              <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                <Sparkles className="w-3 h-3 text-indigo-500" />
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Dedukcja LLM</span>
                <Badge tone="slate">{Math.round(deduction.confidence * 100)}% pewności</Badge>
                {deduction.source_domain && deduction.source_domain !== "unknown" && (
                  <Badge tone={deduction.source_domain === "brutto" ? "amber" : "emerald"}>
                    źródło: {deduction.source_domain}
                  </Badge>
                )}
              </div>
              <p className="text-[11px] text-slate-600 italic leading-relaxed">{deduction.reasoning}</p>
            </section>
          )}

          {/* ── Error (non-blocking) ── */}
          {error && (
            <div className="text-[11px] rounded px-2 py-1.5 border bg-red-50 border-red-200 text-red-800 flex items-start gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* ── Inline form: partial prices ── */}
          {showForm && <PartialPriceForm onDeduce={handleDeduce} onCancel={() => setShowForm(false)} loading={deducing} />}

          {/* ── Actions ── */}
          {!showForm && (
            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={() => handleDeduce()}
                disabled={deducing}
                className="text-[11px] px-2.5 py-1.5 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded font-medium disabled:opacity-50 inline-flex items-center gap-1"
                title="Zrekonstruuj brakujące komponenty ceny przez Gemini"
              >
                {deducing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                Dedukuj ceny (LLM)
              </button>
              <button
                onClick={() => setShowForm(true)}
                className="text-[11px] px-2.5 py-1.5 bg-slate-50 text-slate-700 hover:bg-slate-100 rounded font-medium inline-flex items-center gap-1"
              >
                <Pencil className="w-3 h-3" />
                Wpisz ceny cząstkowe
              </button>
              <button
                onClick={handleConfirm}
                disabled={confirming}
                className="text-[11px] px-2.5 py-1.5 bg-emerald-600 text-white hover:bg-emerald-700 rounded font-medium disabled:opacity-50 inline-flex items-center gap-1 ml-auto"
                title="Zapisz te ceny na stałe — nadpisze niepełną/wadliwą ekstrakcję"
              >
                {confirming ? <Loader2 className="w-3 h-3 animate-spin" /> : <Lock className="w-3 h-3" />}
                Zatwierdź cenę
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Inline partial-price form ──

function DomainToggle({ value, onChange, disabled }: { value: Domain; onChange: (d: Domain) => void; disabled?: boolean }) {
  return (
    <div className="inline-flex border border-slate-300 rounded overflow-hidden text-[9px] font-bold">
      {(["netto", "brutto"] as Domain[]).map((d) => (
        <button
          key={d}
          type="button"
          disabled={disabled}
          onClick={() => onChange(d)}
          className={`px-2 py-0.5 transition-colors ${value === d ? (d === "netto" ? "bg-emerald-100 text-emerald-700" : "bg-blue-100 text-blue-700") : "bg-white text-slate-400 hover:bg-slate-50"}`}
        >
          {d.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

function FormField({
  label,
  value,
  onChange,
  domain,
  onDomain,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  domain: Domain;
  onDomain: (d: Domain) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-0.5">
        <label className="text-[10px] font-medium text-slate-600">{label}</label>
        <DomainToggle value={domain} onChange={onDomain} />
      </div>
      <input
        type="text"
        inputMode="decimal"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full text-xs font-mono border border-slate-300 rounded px-2 py-1 outline-none focus:ring-1 focus:ring-indigo-500 bg-white"
      />
    </div>
  );
}

function PartialPriceForm({
  onDeduce,
  onCancel,
  loading,
}: {
  onDeduce: (known: Record<string, number | null>) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [base, setBase] = useState("");
  const [baseD, setBaseD] = useState<Domain>("netto");
  const [opts, setOpts] = useState("");
  const [optsD, setOptsD] = useState<Domain>("netto");
  const [service, setService] = useState("");
  const [serviceD, setServiceD] = useState<Domain>("netto");
  const [total, setTotal] = useState("");
  const [totalD, setTotalD] = useState<Domain>("brutto");
  const [rabat, setRabat] = useState("");

  const submit = () => {
    const baseN = parseInputNumber(base);
    const optsN = parseInputNumber(opts);
    const serviceN = parseInputNumber(service);
    const totalN = parseInputNumber(total);
    const known: Record<string, number | null> = {
      base_net: baseD === "netto" ? baseN : null,
      base_gross: baseD === "brutto" ? baseN : null,
      options_net: optsD === "netto" ? optsN : null,
      options_gross: optsD === "brutto" ? optsN : null,
      service_net: serviceD === "netto" ? serviceN : null,
      service_gross: serviceD === "brutto" ? serviceN : null,
      total_net: totalD === "netto" ? totalN : null,
      total_gross: totalD === "brutto" ? totalN : null,
      rabat_pln: parseInputNumber(rabat),
    };
    onDeduce(known);
  };

  return (
    <div className="space-y-2 p-3 bg-indigo-50/40 border border-indigo-200 rounded">
      <div className="text-[10px] font-bold uppercase tracking-wider text-indigo-700">
        Ceny cząstkowe — LLM wydedukuje brakujące komponenty
      </div>
      <FormField label="Cena bazowa" value={base} onChange={setBase} domain={baseD} onDomain={setBaseD} placeholder="np. 145485" />
      <FormField label="Opcje fabryczne (Σ)" value={opts} onChange={setOpts} domain={optsD} onDomain={setOptsD} placeholder="np. 12000" />
      <FormField label="Zabudowa / serwis" value={service} onChange={setService} domain={serviceD} onDomain={setServiceD} placeholder="np. 31732" />
      <FormField label="Total" value={total} onChange={setTotal} domain={totalD} onDomain={setTotalD} placeholder="np. 178946" />
      <div>
        <label className="text-[10px] font-medium text-slate-600 block mb-0.5">Rabat (PLN netto)</label>
        <input
          type="text"
          inputMode="decimal"
          value={rabat}
          onChange={(e) => setRabat(e.target.value)}
          placeholder="np. 42317"
          className="w-full text-xs font-mono border border-slate-300 rounded px-2 py-1 outline-none focus:ring-1 focus:ring-indigo-500 bg-white"
        />
      </div>
      <div className="flex items-center justify-end gap-2 pt-1">
        <button onClick={onCancel} disabled={loading} className="text-xs px-3 py-1.5 bg-white text-slate-600 hover:bg-slate-100 rounded-md font-medium border border-slate-200 disabled:opacity-50">
          <X className="w-3.5 h-3.5 inline mr-1" />
          Anuluj
        </button>
        <button onClick={submit} disabled={loading} className="text-xs px-3 py-1.5 bg-indigo-600 text-white hover:bg-indigo-700 rounded-md font-medium disabled:opacity-50">
          {loading ? <Loader2 className="w-3.5 h-3.5 inline mr-1 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 inline mr-1" />}
          Dedukuj z tych wartości
        </button>
      </div>
    </div>
  );
}

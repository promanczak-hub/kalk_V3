import { useState } from "react";
import { ChevronDown, ChevronUp, ScanSearch, AlertTriangle, CheckCircle2, HelpCircle, Pencil, Save, X, Loader2, RefreshCw } from "lucide-react";
import type { DiscountBreakdown, DiscountExtractionMethod, PriceValidation } from "../../types";
import { apiClient } from "../../../lib/apiClient";
import { revalidateVehicleQuiet } from "../../hooks/useRevalidateVehicle";

interface DiscountAuditCardProps {
  vehicleId: string;
  discount: DiscountBreakdown | null | undefined;
  priceValidation?: PriceValidation | null;
  activeMode: "offer" | "suggested" | "custom";
  activeDiscountPct: number;
  activeDiscountAmountNet: number;
  discountableBaseNet: number;
  nonDiscountableTotalNet: number;
  onUpdated?: () => void;
}

const METHOD_LABEL: Record<DiscountExtractionMethod, string> = {
  explicit_amount: "Kwota PLN przepisana z PDF",
  explicit_percentage: "Procent przepisany z PDF",
  computed_from_total: "Wyliczone pośrednio (różnica cen)",
  none: "Brak rabatu",
};

const fmtPln = (v: number | null | undefined): string => {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${v.toLocaleString("pl-PL", { maximumFractionDigits: 0 })} zł`;
};

const fmtPct = (v: number | null | undefined): string => {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${v.toFixed(2)}%`;
};

const parseInputNumber = (s: string): number | null => {
  if (!s.trim()) return null;
  const cleaned = s.replace(/\s/g, "").replace(",", ".");
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
};

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const tone =
    confidence >= 0.85
      ? { bg: "bg-emerald-100", text: "text-emerald-700", icon: CheckCircle2 }
      : confidence >= 0.6
        ? { bg: "bg-amber-100", text: "text-amber-700", icon: AlertTriangle }
        : { bg: "bg-red-100", text: "text-red-700", icon: AlertTriangle };
  const Icon = tone.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${tone.bg} ${tone.text}`}>
      <Icon className="w-3 h-3" />
      {pct}% pewności
    </span>
  );
}

function Row({
  label,
  value,
  hint,
  bold,
  warn,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  bold?: boolean;
  warn?: boolean;
}) {
  return (
    <div className={`flex items-baseline justify-between gap-3 py-1 border-b border-slate-100 last:border-b-0 ${warn ? "bg-amber-50/50 px-2 -mx-2 rounded" : ""}`}>
      <div className="flex items-center gap-1 text-[11px] text-slate-500">
        <span>{label}</span>
        {hint && (
          <span title={hint}>
            <HelpCircle className="w-3 h-3 text-slate-400" />
          </span>
        )}
      </div>
      <span className={`text-xs ${bold ? "font-bold text-slate-900" : "font-medium text-slate-700"} font-mono`}>
        {value}
      </span>
    </div>
  );
}

interface EditFormProps {
  initialPln: number | null;
  initialBase: number | null;
  initialNonDisc: number | null;
  onSave: (vals: { pln: number | null; base: number | null; nonDisc: number | null; note: string }) => Promise<void>;
  onCancel: () => void;
  saving: boolean;
}

type Domain = "netto" | "brutto";

/** Konwertuje wpisaną wartość do netto na podstawie wybranej domeny.
 * Backend (`/api/extract/discount-override`) oczekuje wszystkich kwot w netto. */
const toNet = (raw: number | null, domain: Domain): number | null =>
  raw === null ? null : domain === "brutto" ? +(raw / 1.23).toFixed(2) : raw;

function DomainToggle({
  value,
  onChange,
  disabled,
}: { value: Domain; onChange: (d: Domain) => void; disabled?: boolean }) {
  return (
    <div className="inline-flex border border-slate-300 rounded overflow-hidden text-[9px] font-bold">
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange("netto")}
        className={`px-2 py-0.5 transition-colors ${
          value === "netto"
            ? "bg-emerald-100 text-emerald-700"
            : "bg-white text-slate-400 hover:bg-slate-50"
        }`}
      >
        NETTO
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange("brutto")}
        className={`px-2 py-0.5 transition-colors ${
          value === "brutto"
            ? "bg-blue-100 text-blue-700"
            : "bg-white text-slate-400 hover:bg-slate-50"
        }`}
      >
        BRUTTO
      </button>
    </div>
  );
}

function EditForm({ initialPln, initialBase, initialNonDisc, onSave, onCancel, saving }: EditFormProps) {
  const [pln, setPln] = useState<string>(initialPln !== null ? String(initialPln) : "");
  const [base, setBase] = useState<string>(initialBase !== null ? String(initialBase) : "");
  const [nonDisc, setNonDisc] = useState<string>(initialNonDisc !== null ? String(initialNonDisc) : "");
  const [note, setNote] = useState("");
  const [plnDomain, setPlnDomain] = useState<Domain>("netto");
  const [baseDomain, setBaseDomain] = useState<Domain>("netto");
  const [nonDiscDomain, setNonDiscDomain] = useState<Domain>("netto");

  const parsedPlnNet = toNet(parseInputNumber(pln), plnDomain);
  const parsedBaseNet = toNet(parseInputNumber(base), baseDomain);
  const parsedNonDiscNet = toNet(parseInputNumber(nonDisc), nonDiscDomain);

  const previewPct =
    parsedPlnNet !== null && parsedBaseNet !== null && parsedBaseNet > 0
      ? ((parsedPlnNet / parsedBaseNet) * 100).toFixed(2)
      : null;

  const handleSubmit = async () => {
    await onSave({
      pln: parsedPlnNet,
      base: parsedBaseNet,
      nonDisc: parsedNonDiscNet,
      note: note.trim(),
    });
  };

  const inputCls =
    "w-full text-xs font-mono border border-slate-300 rounded px-2 py-1 outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 bg-white";

  // Podgląd "= X PLN netto" gdy user wpisał w brutto.
  const fmtNetHint = (n: number | null, d: Domain): string | null =>
    d === "brutto" && n !== null && !Number.isNaN(n)
      ? `= ${n.toLocaleString("pl-PL", { maximumFractionDigits: 2 })} PLN netto (÷1.23)`
      : null;

  return (
    <div className="space-y-2 p-3 bg-amber-50/40 border border-amber-200 rounded">
      <div className="text-[10px] font-bold uppercase tracking-wider text-amber-700">
        Manualna korekta — zapis: extraction_method=explicit_amount, confidence=1.0. Wartości w brutto konwertowane ÷1.23 przed POST.
      </div>

      <div>
        <div className="flex items-center justify-between mb-0.5">
          <label className="text-[10px] font-medium text-slate-600">Kwota rabatu (PLN)</label>
          <DomainToggle value={plnDomain} onChange={setPlnDomain} disabled={saving} />
        </div>
        <input
          type="text"
          inputMode="decimal"
          value={pln}
          onChange={(e) => setPln(e.target.value)}
          placeholder={plnDomain === "brutto" ? "np. 52050" : "np. 42317"}
          className={inputCls}
        />
        {fmtNetHint(parsedPlnNet, plnDomain) && (
          <div className="text-[9px] text-slate-400 mt-0.5 font-mono">{fmtNetHint(parsedPlnNet, plnDomain)}</div>
        )}
      </div>

      <div>
        <div className="flex items-center justify-between mb-0.5">
          <label className="text-[10px] font-medium text-slate-600">Podstawa rabatu (PLN) — base + opcje fabryczne</label>
          <DomainToggle value={baseDomain} onChange={setBaseDomain} disabled={saving} />
        </div>
        <input
          type="text"
          inputMode="decimal"
          value={base}
          onChange={(e) => setBase(e.target.value)}
          placeholder={baseDomain === "brutto" ? "np. 178946" : "np. 145485"}
          className={inputCls}
        />
        {fmtNetHint(parsedBaseNet, baseDomain) && (
          <div className="text-[9px] text-slate-400 mt-0.5 font-mono">{fmtNetHint(parsedBaseNet, baseDomain)}</div>
        )}
      </div>

      <div>
        <div className="flex items-center justify-between mb-0.5">
          <label className="text-[10px] font-medium text-slate-600">Poza rabatem (PLN) — zabudowy / dealer extras</label>
          <DomainToggle value={nonDiscDomain} onChange={setNonDiscDomain} disabled={saving} />
        </div>
        <input
          type="text"
          inputMode="decimal"
          value={nonDisc}
          onChange={(e) => setNonDisc(e.target.value)}
          placeholder={nonDiscDomain === "brutto" ? "np. 39031" : "np. 31732"}
          className={inputCls}
        />
        {fmtNetHint(parsedNonDiscNet, nonDiscDomain) && (
          <div className="text-[9px] text-slate-400 mt-0.5 font-mono">{fmtNetHint(parsedNonDiscNet, nonDiscDomain)}</div>
        )}
      </div>

      <div>
        <label className="text-[10px] font-medium text-slate-600 block mb-0.5">
          Notatka audytowa (opcjonalna)
        </label>
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="np. Skorygowano zabudowę wywrotka 31 732 zł"
          className={inputCls}
        />
      </div>

      {previewPct && (
        <div className="text-[11px] text-emerald-700 font-mono pt-1">
          Przeliczony rabat: <strong>{previewPct}%</strong> (z wartości netto)
        </div>
      )}

      <div className="flex items-center justify-end gap-2 pt-1">
        <button
          onClick={onCancel}
          disabled={saving}
          className="text-xs px-3 py-1.5 bg-white text-slate-600 hover:bg-slate-100 rounded-md font-medium border border-slate-200 disabled:opacity-50"
        >
          <X className="w-3.5 h-3.5 inline mr-1" />
          Anuluj
        </button>
        <button
          onClick={handleSubmit}
          disabled={saving}
          className="text-xs px-3 py-1.5 bg-emerald-600 text-white hover:bg-emerald-700 rounded-md font-medium disabled:opacity-50"
        >
          {saving ? (
            <Loader2 className="w-3.5 h-3.5 inline mr-1 animate-spin" />
          ) : (
            <Save className="w-3.5 h-3.5 inline mr-1" />
          )}
          Zapisz korektę
        </button>
      </div>
    </div>
  );
}

export function DiscountAuditCard({
  vehicleId,
  discount,
  priceValidation,
  activeMode,
  activeDiscountPct,
  activeDiscountAmountNet,
  discountableBaseNet,
  nonDiscountableTotalNet,
  onUpdated,
}: DiscountAuditCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [backfilling, setBackfilling] = useState(false);

  // Filter discount-related warnings only
  const discountWarnings = (priceValidation?.warnings || []).filter((w) =>
    w.rule.startsWith("DISCOUNT_") || w.rule === "DEALER_EXTRA_NOT_IN_NON_DISCOUNTABLE" || w.rule === "DEALER_EXTRA_DETECTED"
  );

  const hasIssues = discountWarnings.some((w) => w.severity === "ERROR" || w.severity === "WARNING");
  const hasParsedDiscount = Boolean(discount && discount.extraction_method !== "none");

  if (!hasParsedDiscount && activeDiscountPct <= 0 && !hasIssues) {
    return null;
  }

  const modeLabel =
    activeMode === "offer" ? "Oferta (z PDF)" : activeMode === "suggested" ? "Express (matryca DB)" : "Własny (manualnie)";

  const headerTone = hasIssues
    ? "border-amber-200 bg-amber-50/30"
    : hasParsedDiscount
      ? "border-emerald-200 bg-emerald-50/30"
      : "border-slate-200 bg-white";

  const handleSaveOverride = async ({
    pln,
    base,
    nonDisc,
    note,
  }: {
    pln: number | null;
    base: number | null;
    nonDisc: number | null;
    note: string;
  }) => {
    setSaving(true);
    try {
      const res = await apiClient.fetch(`/api/extract/discount-override/${vehicleId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          explicit_rabat_pln: pln,
          discountable_base_net: base,
          non_discountable_total_net: nonDisc,
          audit_note: note || null,
        }),
      });
      if (!res.ok) throw new Error("Nie udało się zapisać korekty rabatu");
      setIsEditing(false);
      // Re-validate after discount edit — rabat changes often resolve
      // DISCOUNT_PCT_LOW / DEALER_EXTRA warnings → status flips to completed
      await revalidateVehicleQuiet(vehicleId);
      onUpdated?.();
    } catch (e) {
      console.error(e);
      alert("Nie udało się zapisać korekty rabatu — sprawdź konsolę.");
    } finally {
      setSaving(false);
    }
  };

  const handleBackfill = async () => {
    setBackfilling(true);
    try {
      const res = await apiClient.fetch(`/api/extract/backfill-discount/${vehicleId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ overwrite_existing: false }),
      });
      if (!res.ok) throw new Error("Backfill failed");
      await revalidateVehicleQuiet(vehicleId);
      onUpdated?.();
    } catch (e) {
      console.error(e);
      alert("Nie udało się odświeżyć ekstrakcji rabatu — sprawdź konsolę.");
    } finally {
      setBackfilling(false);
    }
  };

  return (
    <div className={`rounded-lg border ${headerTone}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-slate-50/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <ScanSearch className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-semibold text-slate-700">Audyt rabatu</span>
          <span className="text-[10px] text-slate-500">·</span>
          <span className="text-[10px] font-medium text-slate-500">tryb {modeLabel}</span>
          {discount && hasParsedDiscount && <ConfidenceBadge confidence={discount.confidence} />}
          {hasIssues && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-700">
              <AlertTriangle className="w-3 h-3" />
              {discountWarnings.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="font-mono font-bold text-slate-800">{activeDiscountPct.toFixed(2)}%</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-3 border-t border-current/5">
          <section>
            <div className="flex items-center justify-between mb-1.5 mt-2">
              <h6 className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Aktywny rabat (mod: {modeLabel})
              </h6>
              {!isEditing && (
                <div className="flex items-center gap-1">
                  <button
                    onClick={handleBackfill}
                    disabled={backfilling}
                    title="Przelicz rabat deterministycznie z PDF (regex + heurystyki)"
                    className="text-[10px] px-2 py-1 bg-blue-50 text-blue-700 hover:bg-blue-100 rounded font-medium disabled:opacity-50 inline-flex items-center gap-1"
                  >
                    {backfilling ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <RefreshCw className="w-3 h-3" />
                    )}
                    Re-extract
                  </button>
                  <button
                    onClick={() => setIsEditing(true)}
                    className="text-[10px] px-2 py-1 bg-amber-50 text-amber-700 hover:bg-amber-100 rounded font-medium inline-flex items-center gap-1"
                    title="Skoryguj rabat inline"
                  >
                    <Pencil className="w-3 h-3" />
                    Skoryguj ręcznie
                  </button>
                </div>
              )}
            </div>
            <Row label="Procent" value={fmtPct(activeDiscountPct)} bold />
            <Row label="Kwota netto" value={fmtPln(activeDiscountAmountNet)} bold />
            <Row
              label="Stosowana podstawa"
              value={fmtPln(discountableBaseNet)}
              hint="base_price + opcje fabryczne (bez no_discount)"
            />
            <Row
              label="Poza rabatem"
              value={fmtPln(nonDiscountableTotalNet)}
              hint="Zabudowy / akcesoria dealera / pakiety serwisowe — dodawane do total bez %"
            />
          </section>

          {isEditing && (
            <EditForm
              initialPln={discount?.explicit_rabat_pln ?? null}
              initialBase={discount?.discountable_base_net ?? discountableBaseNet}
              initialNonDisc={discount?.non_discountable_total_net ?? nonDiscountableTotalNet}
              onSave={handleSaveOverride}
              onCancel={() => setIsEditing(false)}
              saving={saving}
            />
          )}

          {hasParsedDiscount && discount && !isEditing && (
            <section className="pt-2 border-t border-slate-100">
              <h6 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                Ekstrakcja LLM z PDF
              </h6>
              <Row label="Metoda" value={METHOD_LABEL[discount.extraction_method]} />
              {discount.explicit_rabat_pln !== null && (
                <Row label="Rabat (PLN)" value={fmtPln(discount.explicit_rabat_pln)} />
              )}
              {discount.explicit_rabat_pct !== null && (
                <Row label="Rabat (%) literalny" value={fmtPct(discount.explicit_rabat_pct)} />
              )}
              {discount.discountable_base_net !== null && (
                <Row label="Podstawa LLM" value={fmtPln(discount.discountable_base_net)} />
              )}
              {discount.non_discountable_total_net !== null && (
                <Row label="Poza rabatem LLM" value={fmtPln(discount.non_discountable_total_net)} />
              )}
              {discount.computed_pct !== null && (
                <Row label="Wyliczony %" value={fmtPct(discount.computed_pct)} bold />
              )}

              {discount.audit_notes.length > 0 && (
                <div className="mt-2 space-y-1">
                  {discount.audit_notes.map((note, i) => (
                    <p key={i} className="text-[10px] text-slate-500 italic leading-relaxed">
                      · {note}
                    </p>
                  ))}
                </div>
              )}
            </section>
          )}

          {discountWarnings.length > 0 && !isEditing && (
            <section className="pt-2 border-t border-slate-100">
              <h6 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                Walidator
              </h6>
              <div className="space-y-1.5">
                {discountWarnings.map((w, i) => {
                  const tone =
                    w.severity === "ERROR"
                      ? "bg-red-50 border-red-200 text-red-800"
                      : w.severity === "WARNING"
                        ? "bg-amber-50 border-amber-200 text-amber-800"
                        : "bg-blue-50 border-blue-200 text-blue-800";
                  return (
                    <div key={i} className={`text-[11px] border rounded px-2 py-1.5 ${tone}`}>
                      <div className="flex items-start gap-1.5">
                        <span className="font-bold text-[10px] uppercase opacity-70 flex-shrink-0">
                          {w.rule}
                        </span>
                      </div>
                      <p className="mt-0.5 leading-snug">{w.message}</p>
                    </div>
                  );
                })}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

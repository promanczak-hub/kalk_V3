import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Scale,
  Sparkles,
  Star,
} from "lucide-react";
import type { PriceReconciliation, ReconPath } from "../../types";

interface Props {
  reconciliation: PriceReconciliation | null;
  loading: boolean;
  onRun: () => void;
}

const fmtPln = (v: number | null | undefined): string => {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${v.toLocaleString("pl-PL", { maximumFractionDigits: 0 })} zł`;
};

const VERDICT = {
  ok: { tone: "emerald", icon: CheckCircle2, label: "spójne" },
  ambiguous: { tone: "amber", icon: AlertTriangle, label: "niejednoznaczne" },
  unreconcilable: { tone: "red", icon: AlertTriangle, label: "nie domyka" },
} as const;

const TONE: Record<string, string> = {
  emerald: "bg-emerald-100 text-emerald-700",
  amber: "bg-amber-100 text-amber-700",
  red: "bg-red-100 text-red-700",
  slate: "bg-slate-100 text-slate-600",
};

function Badge({ tone, children }: { tone: keyof typeof TONE; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${TONE[tone]}`}>
      {children}
    </span>
  );
}

function BreakdownRow({ label, net, gross, sign, bold }: { label: string; net: number; gross: number; sign?: string; bold?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1 border-b border-slate-100 last:border-b-0">
      <span className="text-[11px] text-slate-500 truncate">
        {sign && <span className="text-slate-400 font-mono mr-1">{sign}</span>}
        {label}
      </span>
      <div className="flex items-center gap-3 font-mono flex-shrink-0">
        <span className={`text-xs ${bold ? "font-bold text-slate-900" : "font-medium text-slate-600"}`}>{fmtPln(net)}<span className="text-[9px] text-slate-400 ml-0.5">netto</span></span>
        <span className={`text-xs ${bold ? "font-bold text-slate-700" : "text-slate-400"}`}>{fmtPln(gross)}<span className="text-[9px] text-slate-400 ml-0.5">brutto</span></span>
      </div>
    </div>
  );
}

const isWinner = (p: ReconPath, best: ReconPath): boolean =>
  p.source_domain === best.source_domain && p.final_domain === best.final_domain;

export function PriceReconciliationPanel({ reconciliation, loading, onRun }: Props) {
  const r = reconciliation;
  const v = r ? VERDICT[r.verdict] : null;
  const VIcon = v?.icon ?? Scale;

  return (
    <section className="rounded-lg border border-indigo-200 bg-indigo-50/30 p-3 space-y-2">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <Scale className="w-4 h-4 text-indigo-500" />
          <span className="text-xs font-semibold text-slate-700">Audyt 4 ścieżek (net/brutto)</span>
          {r && v && (
            <Badge tone={v.tone}>
              <VIcon className="w-3 h-3" />
              {v.label}
            </Badge>
          )}
          {r && (
            <Badge tone={r.source_domain === "brutto" ? "amber" : "emerald"}>
              źródło: {r.source_domain}
            </Badge>
          )}
        </div>
        <button
          onClick={onRun}
          disabled={loading}
          className="text-[11px] px-2.5 py-1.5 bg-indigo-600 text-white hover:bg-indigo-700 rounded font-medium disabled:opacity-50 inline-flex items-center gap-1"
          title="Przelicz 4 hipotezy net/brutto i pozwól LLM-sędziemu ocenić wynik względem PDF"
        >
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
          {r ? "Przelicz ponownie" : "Uruchom audyt"}
        </button>
      </div>

      {!r && (
        <p className="text-[11px] text-slate-500">
          Liczy rozkład ceny przy 4 założeniach (składniki netto/brutto × cena końcowa
          netto/brutto), wybiera ścieżkę najlepiej domykającą kwoty z PDF i prosi LLM o
          potwierdzenie domeny.
        </p>
      )}

      {r && (
        <>
          {/* Best-path breakdown */}
          <div>
            <h6 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1 mt-1">
              Rozkład (ścieżka zwycięska)
            </h6>
            <BreakdownRow label="Baza katalogowa" net={r.best.base_net} gross={r.best.base_gross} bold />
            <BreakdownRow label="Opcje (Σ)" net={r.best.options_net} gross={r.best.options_gross} sign="+" />
            {r.best.service_net > 0 && (
              <BreakdownRow label="Zabudowa / serwis" net={r.best.service_net} gross={r.best.service_gross} sign="+" />
            )}
            <BreakdownRow label="Rabat" net={-r.best.rabat_net} gross={-r.best.rabat_gross} sign="−" />
            <BreakdownRow label="Total" net={r.best.total_net} gross={r.best.total_gross} bold />
          </div>

          {/* 4-paths comparison */}
          <div>
            <h6 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
              Ścieżki (residuum = odchyłka od kwot z PDF)
            </h6>
            <div className="space-y-0.5">
              {r.all_paths.map((p, i) => {
                const win = isWinner(p, r.best);
                return (
                  <div
                    key={i}
                    className={`flex items-center justify-between gap-2 text-[11px] rounded px-2 py-0.5 ${win ? "bg-emerald-50 font-semibold text-emerald-800" : "text-slate-500"}`}
                  >
                    <span className="inline-flex items-center gap-1 font-mono">
                      {win && <Star className="w-3 h-3 fill-emerald-500 text-emerald-500" />}
                      {p.source_domain}→{p.final_domain}
                    </span>
                    <span className="font-mono">{fmtPln(p.total_gross)} brutto</span>
                    <span className="font-mono">Δ {fmtPln(p.residual_pln)}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Judge */}
          {r.judge && (
            <div className="pt-1 border-t border-slate-100">
              <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                <Sparkles className="w-3 h-3 text-indigo-500" />
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">LLM-sędzia</span>
                <Badge tone={r.judge.agrees_with_winner ? "emerald" : "red"}>
                  {r.judge.agrees_with_winner ? "potwierdza" : "kwestionuje"}
                </Badge>
                {typeof r.judge.confidence === "number" && (
                  <Badge tone="slate">{Math.round(r.judge.confidence * 100)}%</Badge>
                )}
              </div>
              {r.judge.reasoning && (
                <p className="text-[11px] text-slate-600 italic leading-relaxed">{r.judge.reasoning}</p>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}

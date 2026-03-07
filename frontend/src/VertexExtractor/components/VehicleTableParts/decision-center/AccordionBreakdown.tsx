import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { MiniMatrixCell, CostComponent } from "./decision-center.types";
import { fmtPLN2 } from "./decision-center.utils";

interface AccordionBreakdownProps {
  cell: MiniMatrixCell;
}

interface SectionConfig {
  key: string;
  label: string;
  component: CostComponent;
  dotColor: string;
}

function DetailRow({ label, value, muted }: { label: string; value: string; muted?: boolean }) {
  return (
    <div className="flex justify-between items-center py-1">
      <span className={`text-[10px] ${muted ? "text-slate-400" : "text-slate-500"}`}>{label}</span>
      <span className={`text-[10px] font-semibold tabular-nums ${muted ? "text-slate-400" : "text-slate-700"}`}>
        {value}
      </span>
    </div>
  );
}

export function AccordionBreakdown({ cell }: AccordionBreakdownProps) {
  const [openKeys, setOpenKeys] = useState<Set<string>>(new Set());

  const bd = cell.breakdown;
  const sections: SectionConfig[] = [
    { key: "finance", label: "Finanse", component: bd.finance, dotColor: "bg-blue-500" },
    { key: "service", label: "Serwis", component: bd.technical.service, dotColor: "bg-violet-500" },
    { key: "tires", label: "Opony", component: bd.technical.tires, dotColor: "bg-cyan-500" },
    { key: "insurance", label: "Ubezpieczenie", component: bd.technical.insurance, dotColor: "bg-amber-500" },
    { key: "replacement", label: "Auto zastępcze", component: bd.technical.replacement_car, dotColor: "bg-pink-500" },
    { key: "additional", label: "Koszty dodatkowe", component: bd.technical.additional_costs, dotColor: "bg-slate-500" },
  ];

  const toggle = (key: string) => {
    setOpenKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="mt-3 space-y-1">
      {sections.map((section) => {
        const isOpen = openKeys.has(section.key);
        const comp = section.component;
        const marginPct = comp.price > 0 ? ((comp.margin / comp.price) * 100) : 0;

        if (comp.price <= 0 && comp.base <= 0) return null;

        return (
          <div key={section.key} className="border border-slate-100 rounded-lg overflow-hidden">
            {/* Section header */}
            <button
              onClick={() => toggle(section.key)}
              className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-slate-50 transition-colors"
            >
              <div className={`w-2 h-2 rounded-full ${section.dotColor} flex-shrink-0`} />
              <span className="text-[10px] font-semibold text-slate-600 flex-1 uppercase tracking-wider">
                {section.label}
              </span>
              <span className="text-[10px] font-bold text-slate-700 tabular-nums">
                {fmtPLN2(comp.price)} PLN
              </span>
              <ChevronDown
                className={`w-3 h-3 text-slate-400 transition-transform duration-200 ${
                  isOpen ? "rotate-180" : ""
                }`}
              />
            </button>

            {/* Section body */}
            <div
              className={`overflow-hidden transition-all duration-200 ${
                isOpen ? "max-h-48 opacity-100" : "max-h-0 opacity-0"
              }`}
            >
              <div className="px-3 pb-2.5 pt-0.5 border-t border-slate-100">
                <DetailRow label="Koszt bazowy" value={`${fmtPLN2(comp.base)} PLN`} />
                <DetailRow label="Narzut marży" value={`${fmtPLN2(comp.margin)} PLN`} />
                <DetailRow label="Udział marży" value={`${marginPct.toFixed(1)}%`} muted />
                {comp.rozklad_marzy !== undefined && (
                  <DetailRow
                    label="Rozkład marży"
                    value={`${(comp.rozklad_marzy * 100).toFixed(1)}%`}
                    muted
                  />
                )}

                {/* Finance-specific details */}
                {section.key === "finance" && "monthly_pmt_z_czynszem" in comp && (
                  <>
                    <div className="h-px bg-slate-100 my-1.5" />
                    <DetailRow
                      label="PMT z czynszem"
                      value={`${fmtPLN2((comp as CostComponent & { monthly_pmt_z_czynszem?: number }).monthly_pmt_z_czynszem || 0)} PLN`}
                    />
                    <DetailRow
                      label="PMT bez czynszu"
                      value={`${fmtPLN2((comp as CostComponent & { monthly_pmt_bez_czynszu?: number }).monthly_pmt_bez_czynszu || 0)} PLN`}
                    />
                    <DetailRow
                      label="Wykup"
                      value={`${fmtPLN2((comp as CostComponent & { wykup_kwota?: number }).wykup_kwota || 0)} PLN`}
                      muted
                    />
                  </>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

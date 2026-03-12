import type { MiniMatrixCell } from "./decision-center.types";
import { fmtPLN2 } from "./decision-center.utils";

interface AccordionBreakdownProps {
  cell: MiniMatrixCell;
}

interface SectionConfig {
  key: string;
  label: string;
  value: number;
  dotColor: string;
}

export function AccordionBreakdown({ cell }: AccordionBreakdownProps) {
  const sections: SectionConfig[] = [
    { key: "finance", label: "Czynsz Finansowy", value: cell.CzynszFinansowy, dotColor: "bg-blue-500" },
    { key: "service", label: "Serwis", value: cell.Serwis, dotColor: "bg-violet-500" },
    { key: "tires", label: "Opony", value: cell.Opony, dotColor: "bg-cyan-500" },
    { key: "insurance", label: "Ubezpieczenie", value: cell.Ubezpieczenie, dotColor: "bg-amber-500" },
    { key: "replacement", label: "Auto zastępcze", value: cell.SamochodZastepczy, dotColor: "bg-pink-500" },
    { key: "additional", label: "Koszty dodatkowe", value: cell.Admin, dotColor: "bg-slate-500" },
  ];

  return (
    <div className="mt-3 space-y-1">
      {sections.map((section) => {
        if (section.value <= 0) return null;

        return (
          <div key={section.key} className="border border-slate-100 rounded-lg overflow-hidden">
            <div className="w-full flex items-center gap-2 px-3 py-2 text-left bg-slate-50 border-b border-transparent">
              <div className={`w-2 h-2 rounded-full ${section.dotColor} flex-shrink-0`} />
              <span className="text-[10px] font-semibold text-slate-600 flex-1 uppercase tracking-wider">
                {section.label}
              </span>
              <span className="text-[10px] font-bold text-slate-700 tabular-nums">
                {fmtPLN2(section.value)} PLN
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

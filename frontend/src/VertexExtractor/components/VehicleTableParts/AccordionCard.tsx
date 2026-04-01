import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "../../../lib/utils";

interface AccordionCardProps {
  title: ReactNode;
  icon?: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  className?: string;
  headerRight?: ReactNode;
  id?: string;
}

export function AccordionCard({ title, icon, children, defaultOpen = false, className, headerRight, id }: AccordionCardProps) {
  return (
    <details id={id} className={cn("group border border-slate-200 rounded bg-white", className)} open={defaultOpen}>
      <summary className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between cursor-pointer select-none hover:bg-slate-100 transition-colors list-none [&::-webkit-details-marker]:hidden rounded-t ui-accordion-summary">
        <div className="flex items-center gap-2">
          {icon}
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 m-0 leading-none">
            {title}
          </h4>
        </div>
        <div className="flex items-center gap-3">
          {/* headerRight to put buttons without triggering accordion collapse via stopPropagation */}
          {headerRight && (
             <div onClick={(e) => e.stopPropagation()}>
               {headerRight}
             </div>
          )}
          <div className="p-1 rounded hover:bg-slate-200 transition-colors shrink-0">
            <ChevronDown className="w-4 h-4 text-slate-400 group-open:rotate-180 transition-transform" />
          </div>
        </div>
      </summary>
      <div className="p-5">
        {children}
      </div>
    </details>
  );
}

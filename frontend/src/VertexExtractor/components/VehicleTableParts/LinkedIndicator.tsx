import { useState } from "react";

interface LinkedIndicatorProps {
  tableName: string;
  isLinked: boolean;
}

/** Small green/gray dot indicating if a value is linked to a Supabase CRUD table. */
export function LinkedIndicator({ tableName, isLinked }: LinkedIndicatorProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <span
      className="relative inline-flex items-center ml-1.5 cursor-help"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <span
        className={`w-2 h-2 rounded-full ${
          isLinked
            ? "bg-emerald-500 ring-2 ring-emerald-200"
            : "bg-slate-300 ring-2 ring-slate-100"
        }`}
      />
      {showTooltip && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2 py-1 text-[9px] font-medium rounded shadow-lg whitespace-nowrap z-50 bg-slate-800 text-white">
          {isLinked
            ? `Zlinkowane z tabelą: ${tableName}`
            : `Brak powiązania z ${tableName}`}
        </span>
      )}
    </span>
  );
}

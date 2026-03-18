import { useState, useRef, useEffect } from "react";
import { ChevronDown, Check } from "lucide-react";

interface EngineCandidate {
  klasa: string;
  confidence: number;
}

interface EngineCategoryDropdownProps {
  currentCategory: string;
  candidates: EngineCandidate[];
  allEngineTypes?: string[];
  onCategoryChange: (newCategory: string) => void;
  connected?: boolean;
}

export function EngineCategoryDropdown({
  currentCategory,
  candidates,
  allEngineTypes = [],
  onCategoryChange,
  connected,
}: EngineCategoryDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const handleSelect = (klasa: string, e: React.MouseEvent) => {
    e.stopPropagation();
    onCategoryChange(klasa);
    setIsOpen(false);
  };

  const toggleOpen = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpen((prev) => !prev);
  };

  // Shorten display label for the badge
  const shortLabel = (name: string) => {
    if (name.length > 28) return name.slice(0, 25) + "…";
    return name;
  };

  const hasCandidates = candidates.length > 0;
  const candidateKeys = new Set(candidates.map((c) => c.klasa));
  const fallbackTypes = allEngineTypes.filter((k) => !candidateKeys.has(k));
  const isInteractive = hasCandidates || allEngineTypes.length > 0;

  return (
    <div className="relative inline-block" ref={dropdownRef}>
      {/* Trigger badge */}
      <button
        type="button"
        onClick={isInteractive ? toggleOpen : undefined}
        className={`
          inline-flex items-center justify-center gap-1 px-2.5 py-1 text-[11px] font-medium h-full
          transition-colors select-none focus:outline-none focus:ring-inset focus:ring-1 focus:ring-emerald-400
          ${connected ? "" : "border rounded"}
          ${isInteractive
              ? connected
                  ? "bg-emerald-50/50 text-emerald-800 hover:bg-emerald-100 cursor-pointer"
                  : "border-emerald-200 bg-emerald-50 text-emerald-800 hover:bg-emerald-100 hover:border-emerald-300 cursor-pointer"
              : connected
                  ? "bg-slate-50/50 text-slate-600 cursor-default"
                  : "border-slate-200 bg-slate-50 text-slate-600 cursor-default"
          }
        `}
        title={isInteractive ? "Zmień typ silnika" : currentCategory}
        style={{ fontFamily: "'Geist Mono', monospace" }}
      >
        <span>SILNIK: {shortLabel(currentCategory)}</span>
        {isInteractive && (
          <ChevronDown
            className={`w-3 h-3 transition-transform ${isOpen ? "rotate-180" : ""}`}
          />
        )}
      </button>

      {/* Dropdown menu */}
      {isOpen && isInteractive && (
        <div
          className="
            absolute z-50 mt-1 left-0
            w-[380px] max-h-[360px] overflow-y-auto
            bg-white border border-slate-200 rounded-lg shadow-xl
            ring-1 ring-black/5
            animate-in fade-in slide-in-from-top-1 duration-150
          "
        >
          {/* AI candidates section */}
          {hasCandidates && (
            <>
              <div className="px-3 py-2 border-b border-slate-100 bg-slate-50/80 sticky top-0">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Klasyfikacja Napędu AI — ranking
                </span>
              </div>
              {candidates.map((c, idx) => {
                const isSelected = c.klasa === currentCategory;
                const confidencePct = Math.round(c.confidence * 100);

                return (
                  <button
                    key={c.klasa}
                    type="button"
                    onClick={(e) => handleSelect(c.klasa, e)}
                    className={`
                      w-full text-left px-3 py-2 flex items-center gap-2
                      text-xs transition-colors border-b border-slate-50 last:border-b-0
                      ${
                        isSelected
                          ? "bg-emerald-50 text-emerald-900 font-medium"
                          : "hover:bg-slate-50 text-slate-700"
                      }
                    `}
                  >
                    <span className="w-5 text-xs text-slate-400 font-mono tabular-nums flex-shrink-0">
                      {idx + 1}.
                    </span>

                    <div className="w-12 flex-shrink-0">
                      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            confidencePct >= 70
                              ? "bg-emerald-500"
                              : confidencePct >= 30
                                ? "bg-amber-400"
                                : "bg-slate-300"
                          }`}
                          style={{ width: `${Math.max(confidencePct, 2)}%` }}
                        />
                      </div>
                    </div>

                    <span
                      className={`w-10 text-xs font-mono tabular-nums flex-shrink-0 ${
                        confidencePct >= 70
                          ? "text-emerald-600"
                          : confidencePct >= 30
                            ? "text-amber-600"
                            : "text-slate-400"
                      }`}
                    >
                      {confidencePct}%
                    </span>

                    <span className="flex-grow truncate">{c.klasa}</span>

                    {isSelected && (
                      <Check className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                    )}
                  </button>
                );
              })}
            </>
          )}

          {/* All engine types fallback section */}
          {fallbackTypes.length > 0 && (
            <>
              <div className="px-3 py-2 border-b border-slate-100 bg-slate-50/80 sticky top-0">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  {hasCandidates ? "Pozostałe typy silnika" : "Wszystkie typy silnika"}
                </span>
              </div>
              {fallbackTypes.map((klasa) => {
                const isSelected = klasa === currentCategory;
                return (
                  <button
                    key={klasa}
                    type="button"
                    onClick={(e) => handleSelect(klasa, e)}
                    className={`
                      w-full text-left px-3 py-2 flex items-center gap-2
                      text-xs transition-colors border-b border-slate-50 last:border-b-0
                      ${
                        isSelected
                          ? "bg-emerald-50 text-emerald-900 font-medium"
                          : "hover:bg-slate-50 text-slate-700"
                      }
                    `}
                  >
                    <span className="w-5 text-xs text-slate-400 font-mono tabular-nums flex-shrink-0">—</span>
                    <span className="flex-grow truncate">{klasa}</span>
                    {isSelected && (
                      <Check className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                    )}
                  </button>
                );
              })}
            </>
          )}
        </div>
      )}
    </div>
  );
}

import { useState, useRef, useEffect } from "react";
import { ChevronDown, Check } from "lucide-react";

interface VehicleTypeDropdownProps {
  currentType: string;
  onTypeChange: (newType: string) => void;
  connected?: boolean;
}

const OPTIONS = ["Osobowy", "Ciężarowy"];

export function VehicleTypeDropdown({
  currentType,
  onTypeChange,
  connected,
}: VehicleTypeDropdownProps) {
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

  const handleSelect = (type: string, e: React.MouseEvent) => {
    e.stopPropagation();
    onTypeChange(type);
    setIsOpen(false);
  };

  const toggleOpen = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpen((prev) => !prev);
  };

  return (
    <div className="relative inline-block" ref={dropdownRef}>
      <button
        type="button"
        onClick={toggleOpen}
        className={`
          inline-flex items-center justify-center gap-1 px-2.5 py-1 text-[11px] font-medium h-full
          transition-colors select-none focus:outline-none focus:ring-inset focus:ring-1 focus:ring-blue-400
          ${connected ? "" : "border rounded"}
          ${connected
              ? "bg-blue-50/50 text-blue-800 hover:bg-blue-100 cursor-pointer"
              : "border-blue-200 bg-blue-50 text-blue-800 hover:bg-blue-100 hover:border-blue-300 cursor-pointer"
          }
        `}
        title="Zmień kategorię pojazdu"
        style={{ fontFamily: "'Geist Mono', monospace" }}
      >
        <span>{currentType || "Wybierz typ..."}</span>
        <ChevronDown
          className={`w-3 h-3 transition-transform ${isOpen ? "rotate-180" : ""}`}
        />
      </button>

      {isOpen && (
        <div
          className="
            absolute z-50 mt-1 left-0
            w-[180px] bg-white border border-slate-200 rounded-lg shadow-xl
            ring-1 ring-black/5
            animate-in fade-in slide-in-from-top-1 duration-150
          "
        >
          <div className="px-3 py-2 border-b border-slate-100 bg-slate-50/80 sticky top-0">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Kategoria
            </span>
          </div>
          {OPTIONS.map((type) => {
            const isSelected = type === currentType;
            return (
              <button
                key={type}
                type="button"
                onClick={(e) => handleSelect(type, e)}
                className={`
                  w-full text-left px-3 py-2 flex items-center gap-2
                  text-xs transition-colors border-b border-slate-50 last:border-b-0
                  ${
                    isSelected
                      ? "bg-blue-50 text-blue-900 font-medium"
                      : "hover:bg-slate-50 text-slate-700"
                  }
                `}
              >
                <span className="flex-grow truncate">{type}</span>
                {isSelected && (
                  <Check className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

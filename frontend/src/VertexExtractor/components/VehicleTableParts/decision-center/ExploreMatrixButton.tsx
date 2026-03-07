import { Layers, ChevronDown, ChevronUp } from "lucide-react";

interface ExploreMatrixButtonProps {
  isExpanded: boolean;
  onToggle: () => void;
  componentCount?: number;
}

export function ExploreMatrixButton({
  isExpanded,
  onToggle,
  componentCount = 6,
}: ExploreMatrixButtonProps) {
  return (
    <button
      onClick={onToggle}
      className={`
        group flex items-center gap-2.5 w-full px-4 py-3 rounded-xl
        transition-all duration-300 text-left
        ${
          isExpanded
            ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
            : "bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 border border-blue-200 hover:shadow-md hover:border-blue-300"
        }
      `}
    >
      <div
        className={`p-1.5 rounded-lg transition-colors ${
          isExpanded ? "bg-white/20" : "bg-blue-100 group-hover:bg-blue-200"
        }`}
      >
        <Layers className="w-4 h-4" />
      </div>

      <div className="flex-1 min-w-0">
        <span className="text-xs font-bold uppercase tracking-wider">
          {isExpanded ? "Zwiń szczegóły" : "Eksploruj dane Matrix"}
        </span>
      </div>

      {/* Badge */}
      <span
        className={`text-[9px] font-black px-2 py-0.5 rounded-full ${
          isExpanded
            ? "bg-white/20 text-white"
            : "bg-blue-600 text-white"
        }`}
      >
        {componentCount} składowych
      </span>

      {isExpanded ? (
        <ChevronUp className="w-4 h-4 flex-shrink-0" />
      ) : (
        <ChevronDown className="w-4 h-4 flex-shrink-0" />
      )}
    </button>
  );
}

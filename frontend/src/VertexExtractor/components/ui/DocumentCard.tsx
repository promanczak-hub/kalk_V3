import {
  CheckCircle2,
  ChevronRight,
  FileSpreadsheet,
  FileText,
  Loader2,
  X,
} from "lucide-react";
import { cn } from "../../../lib/utils";
import type { UploadedDocument } from "../../types";

export function DocumentCard({
  doc,
  onOpenJson,
  onRemove,
}: {
  doc: UploadedDocument;
  onOpenJson: () => void;
  onRemove?: () => void;
}) {
  const isExcel = doc.type === "excel";

  return (
    <div className="glass-card rounded-2xl p-6 flex flex-col items-center justify-center text-center relative group overflow-hidden">
      {/* Icon Area */}
      <div
        className={cn(
          "relative p-4 rounded-2xl mb-4 transition-transform duration-300 group-hover:scale-110",
          isExcel
            ? "bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400"
            : "bg-rose-100 text-rose-600 dark:bg-rose-900/30 dark:text-rose-400",
        )}
      >
        {isExcel ? (
          <FileSpreadsheet className="w-10 h-10" />
        ) : (
          <FileText className="w-10 h-10" />
        )}

        {/* Status Badge overlaying the icon */}
        {doc.status === "completed" && (
          <div className="absolute -bottom-2 -right-2 bg-white dark:bg-slate-900 rounded-full p-0.5 shadow-sm">
            <CheckCircle2 className="w-6 h-6 text-indigo-500 fill-indigo-100 dark:fill-indigo-900/50" />
          </div>
        )}
      </div>

      <p
        className="font-medium text-slate-800 dark:text-slate-200 text-sm truncate w-full mb-3"
        title={doc.name}
      >
        {doc.name}
      </p>

      {/* Status Indicators */}
      <div className="w-full mt-auto">
        {doc.status === "idle" && (
          <span className="inline-flex items-center text-xs font-medium text-slate-500 bg-slate-100 dark:bg-slate-800 px-2.5 py-1 rounded-full">
            W kolejce
          </span>
        )}
        {doc.status === "uploading" && (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-600 bg-amber-50 dark:text-amber-400 dark:bg-amber-900/20 px-2.5 py-1 rounded-full">
            <Loader2 className="w-3 h-3 animate-spin" />
            Wgrywanie...
          </span>
        )}
        {doc.status === "processing" && (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 dark:text-indigo-400 dark:bg-indigo-900/20 px-2.5 py-1 rounded-full">
            <div className="w-3 h-3 flex items-center justify-center">
              <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-indigo-500"></span>
            </div>
            AI Analiza...
          </span>
        )}
        {doc.status === "completed" && (
          <button
            className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 dark:text-indigo-300 dark:bg-indigo-900/30 dark:hover:bg-indigo-900/50 px-3 py-1.5 rounded-full transition-colors w-full justify-center group/btn"
            onClick={onOpenJson}
          >
            JSON Zapisany
            <ChevronRight className="w-3 h-3 group-hover/btn:translate-x-0.5 transition-transform" />
          </button>
        )}
        {doc.status === "error" && (
          <div className="flex gap-2 w-full">
            <button
              className="inline-flex items-center gap-1 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-full transition-colors flex-1 justify-center"
              onClick={onOpenJson}
            >
              Błąd Analizy
            </button>
            {onRemove && (
              <button
                className="inline-flex items-center justify-center text-red-600 bg-red-50 hover:bg-red-100 p-1.5 rounded-full transition-colors shrink-0"
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove();
                }}
                title="Usuń proces"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

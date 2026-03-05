import { useState, useEffect } from "react";
import { X, Loader2, GitCompareArrows } from "lucide-react";
import type { FleetVehicleView } from "../types";

interface VehicleComparisonModalProps {
  vehicles: FleetVehicleView[];
  onClose: () => void;
}

export function VehicleComparisonModal({
  vehicles,
  onClose,
}: VehicleComparisonModalProps) {
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCompare = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const baseUrl =
        import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
      const response = await fetch(`${baseUrl}/api/compare-vehicles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vehicle_ids: vehicles.map((v) => v.id),
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setMarkdown(data.markdown || "Brak wyniku porównania.");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Nieznany błąd porównania",
      );
    } finally {
      setIsLoading(false);
    }
  };

  // Auto-start comparison on mount
  useEffect(() => {
    handleCompare();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-5xl max-h-[85vh] flex flex-col mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <GitCompareArrows className="w-5 h-5 text-blue-600" />
            <div>
              <h2 className="text-sm font-semibold text-slate-900">
                Porównanie pojazdów ({vehicles.length})
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                {vehicles
                  .map((v) => `${v.brand || "?"} ${v.model || ""}`)
                  .join(" vs ")}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-16">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-4" />
              <p className="text-sm text-slate-600 font-medium">
                Gemini Flash analizuje pojazdy...
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Tabelaryczne porównanie value for money
              </p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
              <p className="font-semibold">Błąd porównania</p>
              <p className="mt-1 text-xs">{error}</p>
              <button
                onClick={handleCompare}
                className="mt-3 text-xs font-bold text-red-600 hover:text-red-800 underline"
              >
                Spróbuj ponownie
              </button>
            </div>
          )}

          {markdown && !isLoading && (
            <div
              className="prose prose-sm max-w-none prose-slate prose-th:text-left prose-th:bg-slate-50 prose-th:px-3 prose-th:py-2 prose-td:px-3 prose-td:py-2 prose-table:border prose-table:border-slate-200 prose-th:border prose-th:border-slate-200 prose-td:border prose-td:border-slate-200 prose-thead:bg-slate-50"
              dangerouslySetInnerHTML={{
                __html: renderMarkdownToHtml(markdown),
              }}
            />
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-100 flex justify-end gap-2">
          {markdown && !isLoading && (
            <button
              onClick={() => {
                navigator.clipboard.writeText(markdown);
              }}
              className="px-4 py-2 text-xs font-semibold text-slate-600 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg transition-colors"
            >
              Kopiuj Markdown
            </button>
          )}
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
          >
            Zamknij
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Simple markdown-to-HTML renderer for tables and basic formatting.
 * Keeps it lightweight without external dependencies.
 */
function renderMarkdownToHtml(md: string): string {
  let html = md;

  // Escape HTML
  html = html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  // Headers
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Italic
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

  // Tables
  const lines = html.split("\n");
  const result: string[] = [];
  let inTable = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    if (line.startsWith("|") && line.endsWith("|")) {
      const cells = line
        .slice(1, -1)
        .split("|")
        .map((c) => c.trim());

      // Check if next line is separator
      const nextLine = lines[i + 1]?.trim() || "";
      const isSeparator = /^\|[\s-|:]+\|$/.test(nextLine);

      if (!inTable) {
        result.push("<table>");
        inTable = true;
      }

      if (isSeparator) {
        // Header row
        result.push(
          "<thead><tr>" +
            cells.map((c) => `<th>${c}</th>`).join("") +
            "</tr></thead><tbody>",
        );
        i++; // Skip separator
      } else {
        result.push(
          "<tr>" + cells.map((c) => `<td>${c}</td>`).join("") + "</tr>",
        );
      }
    } else {
      if (inTable) {
        result.push("</tbody></table>");
        inTable = false;
      }

      // Lists
      if (line.startsWith("- ")) {
        result.push(`<li>${line.slice(2)}</li>`);
      } else if (line === "") {
        result.push("<br/>");
      } else {
        result.push(`<p>${line}</p>`);
      }
    }
  }

  if (inTable) result.push("</tbody></table>");

  return result.join("\n");
}

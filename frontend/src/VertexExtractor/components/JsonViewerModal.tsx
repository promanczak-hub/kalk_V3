import { useState, useMemo, useRef, useEffect } from "react";
import {
  CheckCircle2,
  FileText,
  Loader2,
  X,
  Download,
  Search,
  Send,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import type { UploadedDocument } from "../types";

// Dodajemy pomocniczy interfejs
interface JsonViewerModalProps {
  activeJsonView: UploadedDocument | null;
  onClose: () => void;
  onSaveToDatabase: () => void;
  isSaving: boolean;
}

export function JsonViewerModal({
  activeJsonView,
  onClose,
  onSaveToDatabase,
  isSaving,
}: JsonViewerModalProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [isSendingToKalk, setIsSendingToKalk] = useState(false);
  const [currentMatchIndex, setCurrentMatchIndex] = useState(0);
  const [matchCount, setMatchCount] = useState(0);
  const contentRef = useRef<HTMLPreElement>(null);

  const handleSendToCalculator = async () => {
    if (!activeJsonView || !activeJsonView.jsonResult) return;

    setIsSendingToKalk(true);
    try {
      const parsedJson = JSON.parse(activeJsonView.jsonResult);
      const response = await fetch("http://127.0.0.1:8000/api/kalkulacje", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stan_json: parsedJson }),
      });

      if (!response.ok) {
        throw new Error("Błąd komunikacji z Kalk V3");
      }

      const data = await response.json();
      if (data.id) {
        // Open the calculator in a new tab with the ID
        window.open(`http://localhost:5173/?id=${data.id}`, "_blank");
      }
    } catch (e) {
      console.error(e);
      alert("Nie udało się przekazać oferty do Kalkulatora V3.");
    } finally {
      setIsSendingToKalk(false);
    }
  };

  const highlightedJson = useMemo(() => {
    const rawJson = activeJsonView?.jsonResult || "Brak danych JSON.";

    // Zabezpieczenie HTML
    const escapedJson = rawJson.replace(/</g, "&lt;").replace(/>/g, "&gt;");

    if (!searchQuery.trim()) {
      return escapedJson;
    }

    try {
      const escapedQuery = searchQuery.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const regex = new RegExp(`(${escapedQuery})`, "gi");
      return escapedJson.replace(
        regex,
        '<mark class="search-match cursor-pointer px-0.5 rounded-sm font-medium bg-emerald-200 text-emerald-900">$1</mark>',
      );
    } catch {
      return escapedJson;
    }
  }, [activeJsonView?.jsonResult, searchQuery]);

  // Handle active highlighting and scrolling manually via DOM to avoid re-rendering entire JSON string
  useEffect(() => {
    if (!contentRef.current) return;
    
    // Używamy setTimeout, aby upewnić się, że DOM został już zaktualizowany przez React po dangerouslySetInnerHTML
    const timeoutId = setTimeout(() => {
      if (!contentRef.current) return;
      
      const marks = contentRef.current.querySelectorAll('mark.search-match');
      setMatchCount(marks.length);

      marks.forEach((mark, index) => {
        if (index === currentMatchIndex) {
          mark.classList.remove('bg-emerald-200', 'text-emerald-900');
          mark.classList.add('bg-amber-400', 'text-amber-950', 'ring-2', 'ring-amber-600', 'shadow-sm');
          mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
          mark.classList.remove('bg-amber-400', 'text-amber-950', 'ring-2', 'ring-amber-600', 'shadow-sm');
          mark.classList.add('bg-emerald-200', 'text-emerald-900');
        }
      });
    }, 0);

    return () => clearTimeout(timeoutId);
  }, [highlightedJson, currentMatchIndex]);

  // Reset match index when query changes
  useEffect(() => {
    setCurrentMatchIndex(0);
  }, [searchQuery]);

  const handleNextMatch = () => {
    if (matchCount > 0) {
      setCurrentMatchIndex((prev) => (prev + 1) % matchCount);
    }
  };

  const handlePrevMatch = () => {
    if (matchCount > 0) {
      setCurrentMatchIndex((prev) => (prev - 1 + matchCount) % matchCount);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      if (e.shiftKey) {
        handlePrevMatch();
      } else {
        handleNextMatch();
      }
    }
  };

  if (!activeJsonView) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/20 backdrop-blur-sm animate-in fade-in">
      <div className="bg-white border border-slate-200 w-full max-w-4xl max-h-[90vh] rounded shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95">
        <div className="flex flex-col border-b border-slate-100 bg-slate-50 shrink-0">
          <div className="flex items-center justify-between p-4 pb-2">
            <h3 className="text-base font-medium text-slate-800 flex items-center gap-2">
              <FileText className="w-4 h-4 text-slate-400" />
              {activeJsonView.name}
            </h3>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-800 p-1.5 rounded hover:bg-slate-200 transition-colors"
              title="Zamknij"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="px-4 pb-4">
            <div className="relative w-full flex items-center gap-3">
              <div className="relative flex-1">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="w-4 h-4 text-slate-400" />
                </div>
                <input
                  type="text"
                  placeholder="Wyszukaj w JSON..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="pl-9 pr-4 py-2 w-full text-sm border border-slate-300 rounded focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 focus:outline-none transition-shadow cursor-text"
                />
              </div>
              
              {searchQuery && (
                <div className="flex items-center gap-1 shrink-0 text-sm text-slate-500 select-none">
                  <span className="mr-2 font-medium">
                    {matchCount > 0 ? `${currentMatchIndex + 1} / ${matchCount}` : 'Brak wyników'}
                  </span>
                  <button
                    onClick={handlePrevMatch}
                    disabled={matchCount === 0}
                    className="p-1.5 rounded hover:bg-slate-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-slate-600 focus:outline-none"
                    title="Poprzedni wynik (Shift + Enter)"
                  >
                    <ChevronUp className="w-4 h-4" />
                  </button>
                  <button
                    onClick={handleNextMatch}
                    disabled={matchCount === 0}
                    className="p-1.5 rounded hover:bg-slate-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-slate-600 focus:outline-none"
                    title="Następny wynik (Enter)"
                  >
                    <ChevronDown className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
        
        <div className="p-6 overflow-y-auto flex-1 bg-white custom-scrollbar h-[500px]">
          <pre
            ref={contentRef}
            className="text-xs font-mono text-slate-600 leading-relaxed whitespace-pre-wrap break-all"
            dangerouslySetInnerHTML={{ __html: highlightedJson }}
          />
        </div>

        {/* Footer Toolbar */}
        <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-2">
          {activeJsonView.status !== "error" && (
            <button
              className="flex items-center gap-2 px-4 py-2 rounded text-white bg-emerald-600 hover:bg-emerald-700 transition-colors text-xs font-medium mr-auto"
              onClick={onSaveToDatabase}
              disabled={isSaving}
            >
              {isSaving ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />{" "}
                  Zapisywanie...
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" /> Zapisz w Bazie
                </>
              )}
            </button>
          )}

          {activeJsonView.status !== "error" && (
            <button
              className="flex items-center gap-2 px-4 py-2 rounded text-white bg-blue-600 hover:bg-blue-700 transition-colors text-xs font-medium"
              onClick={handleSendToCalculator}
              disabled={isSendingToKalk}
              title="Przekaż pobrane dane do LTR Kalkulator V3"
            >
              {isSendingToKalk ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Wysyłanie...
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" /> Wyślij do Kalkulatora
                </>
              )}
            </button>
          )}

          <button
            className="flex items-center gap-2 px-4 py-2 rounded text-white bg-slate-800 hover:bg-slate-900 transition-colors text-xs font-medium"
            onClick={() => {
              const blob = new Blob([activeJsonView.jsonResult || ""], {
                type: "application/json",
              });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `synthesis-${activeJsonView.id}.json`;
              a.click();
            }}
          >
            <Download className="w-3.5 h-3.5" />
            Pobierz
          </button>
        </div>
      </div>
    </div>
  );
}

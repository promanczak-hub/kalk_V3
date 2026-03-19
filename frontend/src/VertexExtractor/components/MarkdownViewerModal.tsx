import { useState, useEffect } from "react";
import { X, FileCode, Loader2, Download } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { apiFetch } from "../../lib/api";

interface MarkdownViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentId: string;
  source: "catalog" | "synthesis";
  title?: string;
}

export function MarkdownViewerModal({ isOpen, onClose, documentId, source, title = "Podgląd Markdown" }: MarkdownViewerModalProps) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !documentId) return;

    const fetchMarkdown = async () => {
      setLoading(true);
      setError(null);
      try {
        const url = source === "catalog"
            ? `/api/catalogs/${documentId}/markdown`
            : `/api/extract/${documentId}/markdown`;
          
        const res = await apiFetch(url);
        if (!res.ok) throw new Error("Nie udało się pobrać pliku markdown.");
        const data = await res.json();
        setContent(data.markdown || "Brak treści markdown dla tego dokumentu.");
      } catch (err) {
        console.error(err);
        setError("Wystąpił błąd podczas pobierania.");
      } finally {
        setLoading(false);
      }
    };

    fetchMarkdown();
  }, [isOpen, documentId, source]);

  if (!isOpen) return null;

  const handleDownload = () => {
    if (!content) return;
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `document_${documentId}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-[100] bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b border-slate-200">
          <div className="flex items-center gap-2 text-indigo-700">
            <FileCode className="w-5 h-5" />
            <h2 className="text-lg font-semibold">{title}</h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownload}
              disabled={!content || loading}
              className="flex items-center gap-1 text-sm font-medium px-3 py-1.5 rounded-md bg-indigo-50 text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              Pobierz .md
            </button>
            <button onClick={(e) => { e.stopPropagation(); onClose(); }} className="p-1 hover:bg-slate-100 rounded-md text-slate-500">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-50">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-10 text-slate-500">
              <Loader2 className="w-8 h-8 animate-spin mb-2" />
              <p>Trwa ładowanie dokumentu...</p>
            </div>
          ) : error ? (
            <div className="text-center text-red-500 p-10">{error}</div>
          ) : (
            <div className="prose prose-sm max-w-none bg-white p-8 rounded-lg shadow-sm border border-slate-200 whitespace-pre-wrap" style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace" }}>
              <ReactMarkdown>{content || "Brak treści."}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

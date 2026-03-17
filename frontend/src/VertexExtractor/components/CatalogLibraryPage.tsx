import { useState, useEffect, useCallback } from "react";
import {
  FileText,
  Loader2,
  Trash2,
  Eye,
  X,
  Search,
  RefreshCw,
  BookOpen,
  ArrowRightCircle,
  FileCode,
} from "lucide-react";
import { MarkdownViewerModal } from "./MarkdownViewerModal";

/* ── Types ────────────────────────────────────────────────────── */

interface DocumentLibraryItem {
  id: string;
  uploaded_at: string;
  original_filename: string;
  file_type: string;
  document_type: string;
  brand: string | null;
  model_family: string | null;
  version_tag: string | null;
  extraction_status: string;
  variant_count: number;
}

/* ── Constants ────────────────────────────────────────────────── */

import { apiFetch } from "../../lib/api";

const DOC_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  Katalog: { label: "Katalog", color: "bg-indigo-100 text-indigo-700" },
  Cennik: { label: "Cennik", color: "bg-emerald-100 text-emerald-700" },
  PRICE_LIST: { label: "Cennik", color: "bg-emerald-100 text-emerald-700" },
  BROCHURE: { label: "Broszura", color: "bg-indigo-100 text-indigo-700" },
};

/* ── Component ────────────────────────────────────────────────── */

export function CatalogLibraryPage() {
  const [documents, setDocuments] = useState<DocumentLibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [markdownPreviewId, setMarkdownPreviewId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // ── Fetch documents ───────────────────────────────────────────
  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/api/catalogs`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDocuments(data.catalogs || []);
    } catch (err) {
      console.error("Failed to fetch documents:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // ── Preview ───────────────────────────────────────────────────
  const openPreview = (doc: DocumentLibraryItem) => {
    setPreviewId(doc.id);
    setPdfUrl(`http://localhost:8000/api/catalogs/${doc.id}/file`);
  };

  const closePreview = () => {
    setPreviewId(null);
    setPdfUrl(null);
  };

  // ── Delete ────────────────────────────────────────────────────
  const deleteDocument = async (id: string) => {
    if (!confirm("Czy na pewno usunąć ten dokument z biblioteki?")) return;
    try {
      await apiFetch(`/api/catalogs/${id}`, { method: "DELETE" });
      await fetchDocuments();
      if (previewId === id) closePreview();
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  // ── Reprocess ──────────────────────────────────────────────────
  const reprocessDocument = async (id: string) => {
    if (!confirm("Czy na pewno chcesz przetworzyć ten dokument jako Ofertę (pojedyncze auta)? Zostanie on usunięty z tej biblioteki i trafi do głównej tabeli uwzględniając twarde wypisane ceny i wyposażenie unikalne.")) return;
    try {
      const res = await apiFetch(`/api/catalogs/${id}/reprocess`, { method: "POST" });
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`HTTP ${res.status}: ${errText}`);
      }
      alert("Dokument został przesłany do ponownego przetwarzania jako Oferta. Sprawdź główną tabelę!");
      await fetchDocuments();
      if (previewId === id) closePreview();
    } catch (err) {
      console.error("Reprocess failed:", err);
      alert(`Wystąpił błąd podczas próby ponownego przetworzenia: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  // ── Filter ────────────────────────────────────────────────────
  const filtered = documents.filter((d) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      (d.brand && d.brand.toLowerCase().includes(q)) ||
      (d.model_family && d.model_family.toLowerCase().includes(q)) ||
      (d.original_filename && d.original_filename.toLowerCase().includes(q)) ||
      (d.version_tag && d.version_tag.toLowerCase().includes(q))
    );
  });

  // ── Render ────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-slate-400">
        <Loader2 className="w-6 h-6 animate-spin mr-3" />
        <span>Ładowanie biblioteki cenników...</span>
      </div>
    );
  }

  return (
    <div className="max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-indigo-600" />
            Biblioteka Cenników i Broszur
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Przeglądaj wgrane cenniki i broszury. Dokumenty te są automatycznie kierowane tutaj z głównego widoku.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchDocuments}
            className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
            title="Odśwież"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Szukaj po marce, modelu, pliku lub opisie..."
          className="w-full pl-9 pr-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none bg-white"
        />
      </div>

      {/* Document list */}
      {filtered.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-lg p-12 text-center">
          <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4">
            <BookOpen className="w-7 h-7 text-slate-400" />
          </div>
          <h3 className="text-sm font-semibold text-slate-600 mb-1">
            {documents.length === 0 ? "Brak dokumentów" : "Brak wyników"}
          </h3>
          <p className="text-xs text-slate-400">
            {documents.length === 0
              ? 'Wgraj plik cennika w głównym panelu. Zostanie on tutaj przeniesiony.'
              : "Spróbuj zmienić filtr wyszukiwania."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((doc) => {
            const docTypeStr = typeof doc.document_type === "string" ? doc.document_type.toUpperCase() : "INNE";
            const docType = DOC_TYPE_LABELS[docTypeStr] || {
              label: doc.document_type || "Niezdefiniowano",
              color: "bg-slate-100 text-slate-600",
            };

            return (
              <div
                key={doc.id}
                className="bg-white border border-slate-200 rounded-lg hover:border-indigo-200 hover:shadow-sm transition-all"
              >
                <div className="p-4 flex items-start gap-4">
                  {/* Icon */}
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-red-50 shrink-0 mt-1">
                    <FileText className="w-5 h-5 text-red-500" />
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 border-b border-slate-100 pb-2">
                      <span className="text-sm font-semibold text-slate-700 truncate">
                        {doc.brand} {doc.model_family}
                      </span>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${docType.color}`}
                      >
                        {docType.label}
                      </span>
                      {doc.extraction_status && (
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                          doc.extraction_status === 'ready' ? 'bg-emerald-100 text-emerald-700' :
                          doc.extraction_status === 'extracting' ? 'bg-amber-100 text-amber-700 animate-pulse' :
                          'bg-slate-100 text-slate-600'
                        }`}>
                          Ekstrakcja: {doc.extraction_status}
                        </span>
                      )}
                      {doc.variant_count > 0 && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-100 text-blue-700">
                          Warianty: {doc.variant_count}
                        </span>
                      )}
                      <span className="ml-auto text-xs text-slate-400">
                        Dodano: {new Date(doc.uploaded_at).toLocaleDateString("pl-PL")}
                      </span>
                    </div>

                    <div className="flex flex-col gap-1 text-[11px] text-slate-500">
                      <span className="font-medium text-slate-600 truncate">
                        Plik: {doc.original_filename}
                      </span>
                      {doc.version_tag && (
                        <p className="text-slate-500 leading-relaxed mt-1 bg-slate-50 p-2 rounded border border-slate-100">
                          <strong className="text-slate-600">Tag wersji:</strong> {doc.version_tag}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col items-center gap-2 pl-4 border-l border-slate-100">
                    <button
                      onClick={() => reprocessDocument(doc.id)}
                      className="p-2 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors flex flex-col items-center"
                      title="Przetwarzaj jako Ofertę"
                    >
                      <ArrowRightCircle className="w-5 h-5 mb-1" />
                      <span className="text-[10px] font-medium text-center leading-tight">Jako<br/>Ofertę</span>
                    </button>
                    <button
                      onClick={() => setMarkdownPreviewId(doc.id)}
                      className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors flex flex-col items-center"
                      title="Podgląd MD"
                    >
                      <FileCode className="w-5 h-5 mb-1" />
                      <span className="text-[10px] font-medium">Podgląd MD</span>
                    </button>
                    <button
                      onClick={() => openPreview(doc)}
                      className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors flex flex-col items-center"
                      title="Podgląd PDF"
                    >
                      <Eye className="w-5 h-5 mb-1" />
                      <span className="text-[10px] font-medium">Podgląd PDF</span>
                    </button>
                    <button
                      onClick={() => deleteDocument(doc.id)}
                      className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors flex flex-col items-center"
                      title="Usuń"
                    >
                      <Trash2 className="w-4 h-4 mb-1" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Preview Modal ──────────────────────────────────────── */}
      {previewId && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl max-h-[95vh] flex flex-col overflow-hidden">
            {/* Modal header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 bg-slate-50">
              <h3 className="text-sm font-semibold text-slate-700">
                Podgląd PDF
              </h3>
              <div className="flex gap-2">
                {pdfUrl && (
                  <a
                    href={pdfUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-md transition-colors mr-2 flex items-center justify-center"
                  >
                    Otwórz w nowej karcie
                  </a>
                )}
                <button
                  onClick={closePreview}
                  className="p-1 hover:bg-slate-200 rounded-md transition-colors"
                >
                  <X className="w-5 h-5 text-slate-500" />
                </button>
              </div>
            </div>

            {/* Modal body */}
            <div className="flex-1 overflow-hidden relative" style={{ minHeight: "80vh" }}>
              {pdfUrl ? (
                <iframe
                  src={pdfUrl}
                  className="w-full h-full absolute inset-0 border-0"
                  title="PDF Preview"
                />
              ) : (
                <div className="flex items-center justify-center py-20 text-sm text-slate-400">
                  Brak pliku do podglądu
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Markdown Modal ──────────────────────────────────────── */}
      <MarkdownViewerModal
        isOpen={!!markdownPreviewId}
        onClose={() => setMarkdownPreviewId(null)}
        documentId={markdownPreviewId || ""}
        source="catalog"
      />
    </div>
  );
}

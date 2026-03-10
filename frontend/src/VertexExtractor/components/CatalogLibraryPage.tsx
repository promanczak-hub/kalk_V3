import { useState, useEffect, useCallback, useRef } from "react";
import {
  Upload,
  FileSpreadsheet,
  FileText,
  Loader2,
  Trash2,
  Eye,
  Zap,
  CheckCircle2,
  AlertCircle,
  Clock,
  X,
  ChevronDown,
  ChevronRight,
  Search,
  RefreshCw,
  BookOpen,
} from "lucide-react";

/* ── Types ────────────────────────────────────────────────────── */

interface CatalogItem {
  id: string;
  brand: string;
  model_family: string;
  document_type: "catalog" | "price_list";
  display_name: string;
  version_tag: string | null;
  is_active: boolean;
  file_type: string;
  original_filename: string | null;
  extraction_status: "pending" | "extracting" | "ready" | "error";
  variant_count: number;
  uploaded_at: string;
}

interface XlsxCell {
  v: string | number | boolean | null;
  bg?: string;
  bold?: boolean;
  colspan?: number;
  rowspan?: number;
}

interface XlsxSheet {
  name: string;
  rows: (XlsxCell | null)[][];
  col_widths: number[];
  merge_ranges: unknown[];
  row_count: number;
  col_count: number;
}

/* ── Constants ────────────────────────────────────────────────── */

const BASE_URL = import.meta.env.VITE_API_URL || "";

const STATUS_CONFIG = {
  pending: { icon: Clock, color: "text-slate-400", bg: "bg-slate-50", label: "Oczekuje" },
  extracting: { icon: Loader2, color: "text-amber-500", bg: "bg-amber-50", label: "Ekstrakcja..." },
  ready: { icon: CheckCircle2, color: "text-emerald-600", bg: "bg-emerald-50", label: "Gotowy" },
  error: { icon: AlertCircle, color: "text-red-500", bg: "bg-red-50", label: "Błąd" },
} as const;

const DOC_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  catalog: { label: "Katalog", color: "bg-indigo-100 text-indigo-700" },
  price_list: { label: "Cennik", color: "bg-emerald-100 text-emerald-700" },
};

/* ── Component ────────────────────────────────────────────────── */

export function CatalogLibraryPage() {
  const [catalogs, setCatalogs] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [previewType, setPreviewType] = useState<string>("");
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [xlsxData, setXlsxData] = useState<XlsxSheet[] | null>(null);
  const [activeSheet, setActiveSheet] = useState(0);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedVariants, setExpandedVariants] = useState<string | null>(null);
  const [variantData, setVariantData] = useState<Record<string, Array<Record<string, string | number | null>>>>({});

  // Upload form
  const [uploadBrand, setUploadBrand] = useState("");
  const [uploadModel, setUploadModel] = useState("");
  const [uploadDocType, setUploadDocType] = useState<"catalog" | "price_list">("catalog");
  const [uploadName, setUploadName] = useState("");
  const [uploadVersion, setUploadVersion] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // ── Fetch catalogs ────────────────────────────────────────────
  const fetchCatalogs = useCallback(async () => {
    try {
      const res = await fetch(`${BASE_URL}/api/catalogs`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCatalogs(data.catalogs || []);
    } catch (err) {
      console.error("Failed to fetch catalogs:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCatalogs();
  }, [fetchCatalogs]);

  // ── Upload ────────────────────────────────────────────────────
  const handleUpload = async () => {
    if (!selectedFile || !uploadBrand || !uploadModel || !uploadName) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", selectedFile);
      form.append("brand", uploadBrand);
      form.append("model_family", uploadModel);
      form.append("document_type", uploadDocType);
      form.append("display_name", uploadName);
      if (uploadVersion) form.append("version_tag", uploadVersion);

      const res = await fetch(`${BASE_URL}/api/catalogs/upload`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}`);
      }
      // Reset form
      setShowUpload(false);
      setSelectedFile(null);
      setUploadBrand("");
      setUploadModel("");
      setUploadName("");
      setUploadVersion("");
      await fetchCatalogs();
    } catch (err) {
      console.error("Upload failed:", err);
      alert(`Błąd uploadu: ${err}`);
    } finally {
      setUploading(false);
    }
  };

  // ── Preview ───────────────────────────────────────────────────
  const openPreview = async (catalog: CatalogItem) => {
    setPreviewId(catalog.id);
    setPreviewType(catalog.file_type);
    setPreviewLoading(true);
    setXlsxData(null);
    setPdfUrl(null);

    try {
      if (catalog.file_type === "pdf") {
        const res = await fetch(`${BASE_URL}/api/catalogs/${catalog.id}/file`);
        if (!res.ok) throw new Error("File download failed");
        const blob = await res.blob();
        setPdfUrl(URL.createObjectURL(blob));
      } else if (catalog.file_type === "xlsx") {
        const res = await fetch(`${BASE_URL}/api/catalogs/${catalog.id}/xlsx-data`);
        if (!res.ok) throw new Error("XLSX parse failed");
        const data = await res.json();
        setXlsxData(data.sheets || []);
        setActiveSheet(0);
      }
    } catch (err) {
      console.error("Preview failed:", err);
    } finally {
      setPreviewLoading(false);
    }
  };

  const closePreview = () => {
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    setPreviewId(null);
    setPdfUrl(null);
    setXlsxData(null);
  };

  // ── Extract ───────────────────────────────────────────────────
  const triggerExtraction = async (id: string) => {
    try {
      const res = await fetch(`${BASE_URL}/api/catalogs/${id}/extract`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      // Update status locally
      setCatalogs(prev =>
        prev.map(c => c.id === id ? { ...c, extraction_status: "extracting" } : c)
      );
      // Poll for completion
      const poll = setInterval(async () => {
        const r = await fetch(`${BASE_URL}/api/catalogs/${id}`);
        const d = await r.json();
        const cat = d.catalog;
        if (cat.extraction_status !== "extracting") {
          clearInterval(poll);
          fetchCatalogs();
        }
      }, 3000);
    } catch (err) {
      alert(`Błąd ekstrakcji: ${err}`);
    }
  };

  // ── Delete ────────────────────────────────────────────────────
  const deleteCatalog = async (id: string) => {
    if (!confirm("Czy na pewno usunąć ten katalog?")) return;
    try {
      await fetch(`${BASE_URL}/api/catalogs/${id}`, { method: "DELETE" });
      await fetchCatalogs();
      if (previewId === id) closePreview();
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  // ── Toggle variants ───────────────────────────────────────────
  const toggleVariants = async (catalog: CatalogItem) => {
    if (expandedVariants === catalog.id) {
      setExpandedVariants(null);
      return;
    }
    setExpandedVariants(catalog.id);
    if (!variantData[catalog.id]) {
      const res = await fetch(`${BASE_URL}/api/catalogs/${catalog.id}`);
      const data = await res.json();
      const variants = data.catalog?.extracted_data?.variants || [];
      setVariantData(prev => ({ ...prev, [catalog.id]: variants }));
    }
  };

  // ── Filter ────────────────────────────────────────────────────
  const filtered = catalogs.filter(c => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      c.brand.toLowerCase().includes(q) ||
      c.model_family.toLowerCase().includes(q) ||
      c.display_name.toLowerCase().includes(q)
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
            Biblioteka Cenników
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Zarządzaj katalogami i cennikami modeli. Wgraj PDF lub XLSX i uruchom ekstrakcję wariantów.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchCatalogs}
            className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
            title="Odśwież"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <Upload className="w-4 h-4" />
            Wgraj dokument
          </button>
        </div>
      </div>

      {/* Upload form */}
      {showUpload && (
        <div className="bg-white border border-indigo-200 rounded-lg p-5 mb-6 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">Nowy dokument</h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Marka *</label>
              <input
                type="text"
                value={uploadBrand}
                onChange={e => setUploadBrand(e.target.value)}
                placeholder="np. Volkswagen"
                className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Rodzina modeli *</label>
              <input
                type="text"
                value={uploadModel}
                onChange={e => setUploadModel(e.target.value)}
                placeholder="np. Crafter"
                className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Nazwa wyświetlana *</label>
              <input
                type="text"
                value={uploadName}
                onChange={e => setUploadName(e.target.value)}
                placeholder="np. Crafter 2026 v1"
                className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Wersja (tag)</label>
              <input
                type="text"
                value={uploadVersion}
                onChange={e => setUploadVersion(e.target.value)}
                placeholder="np. 2026-Q1"
                className="w-full px-3 py-2 border border-slate-200 rounded-md text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Typ dokumentu *</label>
              <div className="flex gap-2">
                <button
                  onClick={() => setUploadDocType("catalog")}
                  className={`flex-1 py-2 text-sm rounded-md border transition-colors ${uploadDocType === "catalog" ? "bg-indigo-50 border-indigo-300 text-indigo-700 font-medium" : "border-slate-200 text-slate-600 hover:bg-slate-50"}`}
                >
                  📋 Katalog
                </button>
                <button
                  onClick={() => setUploadDocType("price_list")}
                  className={`flex-1 py-2 text-sm rounded-md border transition-colors ${uploadDocType === "price_list" ? "bg-emerald-50 border-emerald-300 text-emerald-700 font-medium" : "border-slate-200 text-slate-600 hover:bg-slate-50"}`}
                >
                  💰 Cennik
                </button>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Plik (PDF / XLSX) *</label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.xlsx,.csv"
                onChange={e => setSelectedFile(e.target.files?.[0] || null)}
                className="w-full text-sm text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200"
              />
            </div>
          </div>
          <div className="flex items-center justify-end gap-3">
            <button
              onClick={() => setShowUpload(false)}
              className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-md transition-colors"
            >
              Anuluj
            </button>
            <button
              onClick={handleUpload}
              disabled={!selectedFile || !uploadBrand || !uploadModel || !uploadName || uploading}
              className="flex items-center gap-2 px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
              {uploading ? "Wgrywanie..." : "Wgraj"}
            </button>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="relative mb-4">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="Szukaj po marce, modelu lub nazwie..."
          className="w-full pl-9 pr-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none bg-white"
        />
      </div>

      {/* Catalog list */}
      {filtered.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-lg p-12 text-center">
          <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4">
            <BookOpen className="w-7 h-7 text-slate-400" />
          </div>
          <h3 className="text-sm font-semibold text-slate-600 mb-1">
            {catalogs.length === 0 ? "Brak dokumentów" : "Brak wyników"}
          </h3>
          <p className="text-xs text-slate-400">
            {catalogs.length === 0
              ? 'Kliknij "Wgraj dokument" aby dodać katalog lub cennik.'
              : "Spróbuj zmienić filtr wyszukiwania."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(cat => {
            const statusCfg = STATUS_CONFIG[cat.extraction_status];
            const StatusIcon = statusCfg.icon;
            const docType = DOC_TYPE_LABELS[cat.document_type] || { label: cat.document_type, color: "bg-slate-100 text-slate-600" };
            const isExpanded = expandedVariants === cat.id;
            const variants = (variantData[cat.id] || []) as Array<Record<string, string | number | null>>;

            return (
              <div key={cat.id} className="bg-white border border-slate-200 rounded-lg hover:border-indigo-200 hover:shadow-sm transition-all">
                <div className="p-4 flex items-center gap-4">
                  {/* Icon */}
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${cat.file_type === "pdf" ? "bg-red-50" : "bg-emerald-50"}`}>
                    {cat.file_type === "pdf"
                      ? <FileText className="w-5 h-5 text-red-500" />
                      : <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
                    }
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-semibold text-slate-700 truncate">{cat.display_name}</span>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${docType.color}`}>{docType.label}</span>
                      {cat.version_tag && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600">{cat.version_tag}</span>
                      )}
                      {cat.is_active && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-100 text-green-700">Aktywna</span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-slate-400">
                      <span className="font-medium text-slate-500">{cat.brand} / {cat.model_family}</span>
                      <span>{cat.original_filename}</span>
                      <span>{new Date(cat.uploaded_at).toLocaleDateString("pl-PL")}</span>
                    </div>
                  </div>

                  {/* Status */}
                  <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusCfg.bg} ${statusCfg.color}`}>
                    <StatusIcon className={`w-3.5 h-3.5 ${cat.extraction_status === "extracting" ? "animate-spin" : ""}`} />
                    {statusCfg.label}
                    {cat.extraction_status === "ready" && (
                      <span className="font-bold ml-1">{cat.variant_count} war.</span>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1">
                    {cat.extraction_status === "ready" && (
                      <button
                        onClick={() => toggleVariants(cat)}
                        className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                        title="Warianty"
                      >
                        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </button>
                    )}
                    <button
                      onClick={() => openPreview(cat)}
                      className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                      title="Podgląd pliku"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    {(cat.extraction_status === "pending" || cat.extraction_status === "error") && (
                      <button
                        onClick={() => triggerExtraction(cat.id)}
                        className="p-2 text-slate-400 hover:text-amber-600 hover:bg-amber-50 rounded-lg transition-colors"
                        title="Uruchom ekstrakcję"
                      >
                        <Zap className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => deleteCatalog(cat.id)}
                      className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                      title="Usuń"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Expanded variants */}
                {isExpanded && variants.length > 0 && (
                  <div className="border-t border-slate-100 px-4 py-3 bg-slate-50/50">
                    <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
                      Wyekstrahowane warianty ({variants.length})
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                      {variants.map((v, idx) => (
                        <div key={idx} className="bg-white border border-slate-200 rounded-md p-2.5 text-xs">
                          <div className="font-medium text-slate-700 mb-1 truncate">
                            {(v.variant_name as string) || `Wariant ${idx + 1}`}
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {v.body_type && (
                              <span className="px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600 text-[10px]">{v.body_type as string}</span>
                            )}
                            {v.engine_power_hp && (
                              <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 text-[10px]">{v.engine_power_hp as string} KM</span>
                            )}
                            {v.drive_type && (
                              <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 text-[10px]">{v.drive_type as string}</span>
                            )}
                            {v.europallets && (
                              <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 text-[10px]">{v.europallets as string} pal.</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Preview Modal ──────────────────────────────────────── */}
      {previewId && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">
            {/* Modal header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 bg-slate-50">
              <h3 className="text-sm font-semibold text-slate-700">
                Podgląd dokumentu
              </h3>
              <button onClick={closePreview} className="p-1 hover:bg-slate-200 rounded-md transition-colors">
                <X className="w-4 h-4 text-slate-500" />
              </button>
            </div>

            {/* Modal body */}
            <div className="flex-1 overflow-auto">
              {previewLoading ? (
                <div className="flex items-center justify-center py-20">
                  <Loader2 className="w-6 h-6 animate-spin text-indigo-500 mr-3" />
                  <span className="text-sm text-slate-500">Ładowanie podglądu...</span>
                </div>
              ) : previewType === "pdf" && pdfUrl ? (
                <iframe src={pdfUrl} className="w-full h-[80vh]" title="PDF Preview" />
              ) : previewType === "xlsx" && xlsxData ? (
                <div>
                  {/* Sheet tabs */}
                  {xlsxData.length > 1 && (
                    <div className="flex border-b border-slate-200 bg-slate-50 px-2 pt-1 gap-0.5 overflow-x-auto">
                      {xlsxData.map((sheet, idx) => (
                        <button
                          key={idx}
                          onClick={() => setActiveSheet(idx)}
                          className={`px-3 py-1.5 text-xs font-medium rounded-t-md border border-b-0 transition-colors whitespace-nowrap ${
                            activeSheet === idx
                              ? "bg-white text-indigo-700 border-slate-200"
                              : "text-slate-500 border-transparent hover:text-slate-700 hover:bg-slate-100"
                          }`}
                        >
                          {sheet.name}
                        </button>
                      ))}
                    </div>
                  )}
                  {/* Sheet content */}
                  <div className="overflow-auto max-h-[75vh]">
                    <table className="border-collapse text-xs">
                      <tbody>
                        {xlsxData[activeSheet]?.rows.map((row, rowIdx) => (
                          <tr key={rowIdx} className={rowIdx % 2 === 0 ? "bg-white" : "bg-slate-50/50"}>
                            <td className="px-2 py-1 text-[10px] text-slate-400 bg-slate-100 border border-slate-200 text-center font-mono sticky left-0 z-10">
                              {rowIdx + 1}
                            </td>
                            {row.map((cell, colIdx) => {
                              if (cell === null) return null;
                              return (
                                <td
                                  key={colIdx}
                                  colSpan={cell.colspan || 1}
                                  rowSpan={cell.rowspan || 1}
                                  className="px-2 py-1 border border-slate-200 whitespace-nowrap max-w-[200px] truncate"
                                  style={{
                                    backgroundColor: cell.bg || undefined,
                                    fontWeight: cell.bold ? 600 : 400,
                                    minWidth: `${(xlsxData[activeSheet].col_widths[colIdx] || 10) * 7}px`,
                                  }}
                                  title={cell.v != null ? String(cell.v) : ""}
                                >
                                  {cell.v != null ? String(cell.v) : ""}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center py-20 text-sm text-slate-400">
                  Podgląd niedostępny dla tego formatu
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

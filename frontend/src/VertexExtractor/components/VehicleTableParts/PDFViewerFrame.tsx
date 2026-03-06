import { useState, useEffect, useRef, useCallback } from "react";
import { Loader2, X, ChevronLeft, ChevronRight } from "lucide-react";
import * as pdfjsLib from "pdfjs-dist";
import * as XLSX from "xlsx";

// Use the bundled worker from pdfjs-dist
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

interface DocumentViewerFrameProps {
  rawDocUrl: string;
  brand: string;
  model: string;
}

type FileType = "pdf" | "excel" | "unknown";

function detectFileType(url: string): FileType {
  if (/\.pdf(\?.*)?$/i.test(url)) return "pdf";
  if (/\.(xlsx|xls)(\?.*)?$/i.test(url)) return "excel";
  return "unknown";
}

/* ── Excel sub-component ────────────────────────────────── */

interface ExcelViewerProps {
  rawDocUrl: string;
  brand: string;
  model: string;
}

function ExcelViewer({ rawDocUrl, brand, model }: ExcelViewerProps) {
  const [workbook, setWorkbook] = useState<XLSX.WorkBook | null>(null);
  const [activeSheet, setActiveSheet] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadExcel = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
        const proxyUrl = `${baseUrl}/api/doc-proxy?url=${encodeURIComponent(rawDocUrl)}`;

        const response = await fetch(proxyUrl);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const arrayBuffer = await response.arrayBuffer();
        const wb = XLSX.read(arrayBuffer, { type: "array" });

        if (!cancelled) {
          setWorkbook(wb);
          setActiveSheet(0);
        }
      } catch (err) {
        if (!cancelled) {
          console.error("Excel Load Error:", err);
          setError("Nie udało się załadować pliku Excel.");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    loadExcel();
    return () => { cancelled = true; };
  }, [rawDocUrl]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin mb-4 text-emerald-500" />
        <p className="text-sm font-medium text-slate-500">Trwa ładowanie arkusza Excel...</p>
      </div>
    );
  }

  if (error || !workbook) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-red-500">
        <X className="w-10 h-10 mb-4" />
        <p className="text-sm font-medium mb-4">{error || "Nieznany błąd"}</p>
        <a
          href={rawDocUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="px-4 py-2 bg-blue-600 font-medium text-white rounded-lg shadow-sm hover:bg-blue-700 transition-colors text-sm"
        >
          Otwórz dokument w nowej karcie
        </a>
      </div>
    );
  }

  const sheetNames = workbook.SheetNames;
  const sheet = workbook.Sheets[sheetNames[activeSheet]];
  const rows: unknown[][] = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: "" });

  const headerRow = rows[0] || [];
  const dataRows = rows.slice(1);

  return (
    <>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-slate-200 shrink-0 flex-wrap gap-2">
        <span className="text-xs font-medium text-slate-500">
          {brand} {model}
        </span>

        {/* Sheet tabs */}
        {sheetNames.length > 1 && (
          <div className="flex items-center gap-1">
            {sheetNames.map((name, idx) => (
              <button
                key={name}
                onClick={() => setActiveSheet(idx)}
                className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors ${
                  idx === activeSheet
                    ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                    : "text-slate-500 hover:text-slate-700 hover:bg-slate-100 border border-transparent"
                }`}
              >
                {name}
              </button>
            ))}
          </div>
        )}

        <a
          href={rawDocUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs font-medium text-blue-600 hover:text-blue-800 transition-colors"
        >
          Otwórz w nowej karcie ↗
        </a>
      </div>

      {/* Table area */}
      <div className="overflow-auto bg-white" style={{ maxHeight: "85vh" }}>
        <table className="w-full border-collapse text-xs">
          <thead className="sticky top-0 z-10">
            <tr>
              {headerRow.map((cell, ci) => (
                <th
                  key={ci}
                  className="px-3 py-2 bg-slate-100 border-b border-r border-slate-200 text-left font-semibold text-slate-700 whitespace-nowrap"
                >
                  {String(cell ?? "")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataRows.map((row, ri) => (
              <tr
                key={ri}
                className={ri % 2 === 0 ? "bg-white" : "bg-slate-50/60"}
              >
                {headerRow.map((_, ci) => (
                  <td
                    key={ci}
                    className="px-3 py-1.5 border-b border-r border-slate-100 text-slate-600 whitespace-nowrap"
                  >
                    {String((row as unknown[])[ci] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>

        {dataRows.length === 0 && (
          <div className="text-center py-10 text-slate-400 text-sm">
            Arkusz jest pusty.
          </div>
        )}
      </div>
    </>
  );
}

/* ── PDF sub-component (existing logic, extracted) ────── */

interface PDFViewerProps {
  rawDocUrl: string;
  brand: string;
  model: string;
}

function PDFViewer({ rawDocUrl, brand, model }: PDFViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadPdf = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
        const proxyUrl = `${baseUrl}/api/doc-proxy?url=${encodeURIComponent(rawDocUrl)}`;

        const response = await fetch(proxyUrl);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const arrayBuffer = await response.arrayBuffer();
        const doc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

        if (!cancelled) {
          setPdfDoc(doc);
          setTotalPages(doc.numPages);
          setCurrentPage(1);
        }
      } catch (err) {
        if (!cancelled) {
          console.error("PDF.js Load Error:", err);
          setError("Nie udało się załadować dokumentu PDF.");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    loadPdf();
    return () => { cancelled = true; };
  }, [rawDocUrl]);

  const renderPage = useCallback(async () => {
    if (!pdfDoc || !canvasRef.current || !containerRef.current) return;

    try {
      const page = await pdfDoc.getPage(currentPage);
      const containerWidth = containerRef.current.clientWidth - 32;
      const unscaledViewport = page.getViewport({ scale: 1.0 });
      const fitScale = containerWidth / unscaledViewport.width;
      const viewport = page.getViewport({ scale: fitScale });

      const canvas = canvasRef.current;
      const context = canvas.getContext("2d");
      if (!context) return;

      canvas.width = viewport.width;
      canvas.height = viewport.height;

      await page.render({
        canvasContext: context,
        viewport,
        canvas,
      }).promise;
    } catch (err) {
      console.error("PDF.js Render Error:", err);
    }
  }, [pdfDoc, currentPage]);

  useEffect(() => { renderPage(); }, [renderPage]);

  useEffect(() => {
    const handleResize = () => renderPage();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [renderPage]);

  const goToPrevPage = () => setCurrentPage((p) => Math.max(1, p - 1));
  const goToNextPage = () => setCurrentPage((p) => Math.min(totalPages, p + 1));

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-500" />
        <p className="text-sm font-medium text-slate-500">Trwa ładowanie dokumentu z serwera...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-red-500">
        <X className="w-10 h-10 mb-4" />
        <p className="text-sm font-medium mb-4">{error}</p>
        <a
          href={rawDocUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="px-4 py-2 bg-blue-600 font-medium text-white rounded-lg shadow-sm hover:bg-blue-700 transition-colors text-sm"
        >
          Otwórz dokument w nowej karcie
        </a>
      </div>
    );
  }

  if (!pdfDoc) return null;

  return (
    <>
      {/* Pagination toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-slate-200 shrink-0">
        <span className="text-xs font-medium text-slate-500">
          {brand} {model}
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={goToPrevPage}
            disabled={currentPage <= 1}
            className="p-1.5 rounded-md hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Poprzednia strona"
          >
            <ChevronLeft className="w-4 h-4 text-slate-600" />
          </button>
          <span className="text-xs font-semibold text-slate-700 min-w-[80px] text-center">
            {currentPage} / {totalPages}
          </span>
          <button
            onClick={goToNextPage}
            disabled={currentPage >= totalPages}
            className="p-1.5 rounded-md hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Następna strona"
          >
            <ChevronRight className="w-4 h-4 text-slate-600" />
          </button>
        </div>
        <a
          href={rawDocUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs font-medium text-blue-600 hover:text-blue-800 transition-colors"
        >
          Otwórz w nowej karcie ↗
        </a>
      </div>

      {/* Canvas area */}
      <div
        ref={containerRef}
        className="overflow-y-auto flex justify-center bg-slate-200/60 p-4"
        style={{ maxHeight: "85vh" }}
      >
        <canvas
          ref={canvasRef}
          className="shadow-lg rounded bg-white block"
        />
      </div>
    </>
  );
}

/* ── Main exported component ─────────────────────────────── */

export function DocumentViewerFrame({ rawDocUrl, brand, model }: DocumentViewerFrameProps) {
  const fileType = detectFileType(rawDocUrl);

  return (
    <div className="mt-4 pt-4 border-t border-slate-200 w-full relative bg-slate-100 rounded-lg overflow-hidden flex flex-col">
      {fileType === "pdf" && (
        <PDFViewer rawDocUrl={rawDocUrl} brand={brand} model={model} />
      )}

      {fileType === "excel" && (
        <ExcelViewer rawDocUrl={rawDocUrl} brand={brand} model={model} />
      )}

      {fileType === "unknown" && (
        <div className="flex flex-col items-center justify-center py-20 text-amber-600">
          <X className="w-10 h-10 mb-4" />
          <p className="text-sm font-medium mb-4">
            Nieobsługiwany format dokumentu. Dokument można otworzyć w nowej karcie.
          </p>
          <a
            href={rawDocUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-blue-600 font-medium text-white rounded-lg shadow-sm hover:bg-blue-700 transition-colors text-sm"
          >
            Otwórz dokument w nowej karcie
          </a>
        </div>
      )}
    </div>
  );
}

// Backward-compatible re-export
export { DocumentViewerFrame as PDFViewerFrame };

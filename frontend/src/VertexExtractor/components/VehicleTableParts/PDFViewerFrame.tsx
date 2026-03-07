import { useState, useEffect, useRef, useCallback } from "react";
import { Loader2, X, ZoomIn, ZoomOut, Maximize2, RotateCcw } from "lucide-react";
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

/* ── PDF sub-component — continuous scroll + zoom ────── */

const ZOOM_STEP = 0.15;
const ZOOM_MIN = 0.25;
const ZOOM_MAX = 4.0;
const DEVICE_PIXEL_RATIO = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;

interface PDFViewerProps {
  rawDocUrl: string;
  brand: string;
  model: string;
}

function PDFViewer({ rawDocUrl, brand, model }: PDFViewerProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const pageRefsMap = useRef<Map<number, HTMLCanvasElement>>(new Map());
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState<number | "fit-width">("fit-width");
  const [resolvedScale, setResolvedScale] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const renderGenRef = useRef(0);

  /* ── Load PDF ── */
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

  /* ── Compute fit-width scale ── */
  const computeFitScale = useCallback(async () => {
    if (!pdfDoc || !scrollContainerRef.current) return 1;
    const page = await pdfDoc.getPage(1);
    const vp = page.getViewport({ scale: 1.0 });
    const containerWidth = scrollContainerRef.current.clientWidth - 48; // padding
    return containerWidth / vp.width;
  }, [pdfDoc]);

  /* ── Render all pages ── */
  const renderAllPages = useCallback(async () => {
    if (!pdfDoc) return;
    const gen = ++renderGenRef.current;

    let actualScale: number;
    if (scale === "fit-width") {
      actualScale = await computeFitScale();
    } else {
      actualScale = scale;
    }
    setResolvedScale(actualScale);

    for (let i = 1; i <= pdfDoc.numPages; i++) {
      if (gen !== renderGenRef.current) return; // pre-empted
      const canvas = pageRefsMap.current.get(i);
      if (!canvas) continue;

      try {
        const page = await pdfDoc.getPage(i);
        if (gen !== renderGenRef.current) return;

        const viewport = page.getViewport({ scale: actualScale * DEVICE_PIXEL_RATIO });
        const cssViewport = page.getViewport({ scale: actualScale });

        canvas.width = viewport.width;
        canvas.height = viewport.height;
        canvas.style.width = `${cssViewport.width}px`;
        canvas.style.height = `${cssViewport.height}px`;

        const ctx = canvas.getContext("2d");
        if (!ctx) continue;

        await page.render({ canvasContext: ctx, viewport }).promise;
      } catch (err) {
        console.error(`PDF.js Render Error (page ${i}):`, err);
      }
    }
  }, [pdfDoc, scale, computeFitScale]);

  useEffect(() => { renderAllPages(); }, [renderAllPages]);

  /* ── Re-render on window resize (fit-width) ── */
  useEffect(() => {
    if (scale !== "fit-width") return;
    const handleResize = () => renderAllPages();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [scale, renderAllPages]);

  /* ── Track visible page via IntersectionObserver ── */
  useEffect(() => {
    if (!scrollContainerRef.current || totalPages === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        let topMostPage = currentPage;
        let topMostY = Infinity;
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const pageNum = Number(entry.target.getAttribute("data-page"));
            const rect = entry.boundingClientRect;
            if (rect.top < topMostY) {
              topMostY = rect.top;
              topMostPage = pageNum;
            }
          }
        }
        setCurrentPage(topMostPage);
      },
      {
        root: scrollContainerRef.current,
        threshold: [0, 0.1, 0.25, 0.5],
      }
    );

    pageRefsMap.current.forEach((canvas) => {
      observer.observe(canvas);
    });

    return () => observer.disconnect();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [totalPages, pdfDoc, resolvedScale]);

  /* ── Zoom handlers ── */
  const handleZoomIn = () => {
    setScale((prev) => {
      const current = prev === "fit-width" ? resolvedScale : prev;
      return Math.min(ZOOM_MAX, current + ZOOM_STEP);
    });
  };

  const handleZoomOut = () => {
    setScale((prev) => {
      const current = prev === "fit-width" ? resolvedScale : prev;
      return Math.max(ZOOM_MIN, current - ZOOM_STEP);
    });
  };

  const handleFitWidth = () => setScale("fit-width");
  const handleReset = () => setScale(1);

  const zoomPercentage = Math.round((scale === "fit-width" ? resolvedScale : scale) * 100);

  /* ── Mouse-wheel zoom (Ctrl+Scroll) ── */
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    const handler = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      if (e.deltaY < 0) handleZoomIn();
      else handleZoomOut();
    };
    container.addEventListener("wheel", handler, { passive: false });
    return () => container.removeEventListener("wheel", handler);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolvedScale]);

  /* ── Register canvas ref ── */
  const setCanvasRef = useCallback((pageNum: number) => (el: HTMLCanvasElement | null) => {
    if (el) {
      pageRefsMap.current.set(pageNum, el);
    } else {
      pageRefsMap.current.delete(pageNum);
    }
  }, []);

  /* ── Loading state ── */
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

  const pageNumbers = Array.from({ length: totalPages }, (_, i) => i + 1);

  return (
    <>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-slate-200 shrink-0 flex-wrap gap-2">
        <span className="text-xs font-medium text-slate-500">
          {brand} {model}
        </span>

        {/* Page indicator */}
        <span className="text-xs font-semibold text-slate-700 min-w-[80px] text-center">
          Strona {currentPage} / {totalPages}
        </span>

        {/* Zoom controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={handleZoomOut}
            disabled={zoomPercentage <= Math.round(ZOOM_MIN * 100)}
            className="p-1.5 rounded-md hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Pomniejsz"
          >
            <ZoomOut className="w-4 h-4 text-slate-600" />
          </button>

          <span className="text-[11px] font-semibold text-slate-600 min-w-[44px] text-center tabular-nums">
            {zoomPercentage}%
          </span>

          <button
            onClick={handleZoomIn}
            disabled={zoomPercentage >= Math.round(ZOOM_MAX * 100)}
            className="p-1.5 rounded-md hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Powiększ"
          >
            <ZoomIn className="w-4 h-4 text-slate-600" />
          </button>

          <div className="w-px h-4 bg-slate-200 mx-1" />

          <button
            onClick={handleFitWidth}
            className={`p-1.5 rounded-md transition-colors ${
              scale === "fit-width"
                ? "bg-blue-100 text-blue-700"
                : "hover:bg-slate-100 text-slate-600"
            }`}
            title="Dopasuj do szerokości"
          >
            <Maximize2 className="w-4 h-4" />
          </button>

          <button
            onClick={handleReset}
            className={`p-1.5 rounded-md transition-colors ${
              scale === 1
                ? "bg-blue-100 text-blue-700"
                : "hover:bg-slate-100 text-slate-600"
            }`}
            title="Rozmiar 1:1 (100%)"
          >
            <RotateCcw className="w-4 h-4" />
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

      {/* Scrollable pages area */}
      <div
        ref={scrollContainerRef}
        className="overflow-auto bg-slate-200/60"
        style={{ maxHeight: "85vh" }}
      >
        <div className="flex flex-col items-center gap-4 py-4 px-4">
          {pageNumbers.map((pageNum) => (
            <canvas
              key={pageNum}
              data-page={pageNum}
              ref={setCanvasRef(pageNum)}
              className="shadow-lg rounded bg-white block"
            />
          ))}
        </div>
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

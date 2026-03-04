import React, { useState, useEffect } from "react";
import { X, ExternalLink, Download, Loader2 } from "lucide-react";

interface DocumentViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  pdfUrl: string | null;
  documentName: string;
}

export const DocumentViewerModal: React.FC<DocumentViewerModalProps> = ({
  isOpen,
  onClose,
  pdfUrl,
  documentName,
}) => {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    
    const fetchPdf = async () => {
      if (!isOpen || !pdfUrl) return;
      
      setIsLoading(true);
      setError(null);
      
      try {
        const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
        const proxyUrl = `${baseUrl}/api/pdf-proxy?url=${encodeURIComponent(pdfUrl)}`;
        
        const response = await fetch(proxyUrl);
        if (!response.ok) throw new Error("Błąd pobierania PDF");
        
        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);
        
        if (active) {
          setBlobUrl(objectUrl);
        }
      } catch (err) {
        if (active) {
          console.error("PDF Fetch Error:", err);
          setError("Nie udało się pobrać dokumentu z serwera.");
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    };

    fetchPdf();

    return () => {
      active = false;
    };
  }, [isOpen, pdfUrl]);

  // Oddzielny useEffect do czyszczenia blobUrl przy zamknięciu lub zmianie
  useEffect(() => {
    return () => {
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [blobUrl]);

  if (!isOpen || !pdfUrl) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 sm:p-6 lg:p-12 animate-in fade-in duration-200">
      <div className="bg-white w-full h-full max-w-7xl rounded-xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        
        {/* TOP BAR */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
          <h2 className="text-lg font-semibold text-slate-800 truncate pr-4">
            {documentName}
          </h2>
          
          <div className="flex items-center gap-3 shrink-0">
            <a
              href={pdfUrl}
              download={documentName}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 hover:text-slate-900 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
              title="Pobierz dokument na dysk"
            >
              <Download className="w-4 h-4" />
              <span className="hidden sm:inline">Pobierz (Oryginał)</span>
            </a>
            
            <a
              href={pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-100 rounded-lg hover:bg-blue-100 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
              title="Otwórz dokument w osobnej karcie przeglądarki"
            >
              <ExternalLink className="w-4 h-4" />
              <span className="hidden sm:inline">Otwórz w nowym oknie</span>
            </a>

            <div className="w-px h-6 bg-slate-300 mx-1"></div>

            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-red-500"
              title="Zamknij podgląd dokumentu"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* VIEWER AREA */}
        <div className="flex-1 bg-slate-200/50 w-full h-full relative flex items-center justify-center">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center text-slate-400">
               <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-500" />
               <p className="text-sm font-medium text-slate-500">Trwa ładowanie struktury dokumentu...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center text-red-500">
               <X className="w-10 h-10 mb-4" />
               <p className="text-sm font-medium">{error}</p>
            </div>
          ) : blobUrl ? (
            <object
              data={`${blobUrl}#toolbar=1&navpanes=0&statusbar=0&messages=0`}
              type="application/pdf"
              className="w-full h-full border-0 absolute inset-0 bg-slate-200/50"
              title={`Podgląd dokumentu: ${documentName}`}
            >
              <div className="flex flex-col items-center justify-center p-6 text-center text-slate-500 w-full h-full bg-slate-100 absolute inset-0 z-10">
                 <p className="mb-2">Twoja przeglądarka nie obsługuje wbudowanego podglądu PDF pod tym adresem.</p>
                 <a href={pdfUrl} target="_blank" rel="noopener noreferrer" className="px-4 py-2 mt-2 bg-blue-600 font-medium text-white rounded-lg shadow-sm hover:bg-blue-700 transition-colors">
                   Otwórz dokument w nowej karcie
                 </a>
              </div>
            </object>
          ) : null}
        </div>
      </div>
    </div>
  );
};

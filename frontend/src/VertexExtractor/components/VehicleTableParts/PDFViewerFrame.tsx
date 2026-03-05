import { useState } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "../../../lib/utils";

interface PDFViewerFrameProps {
  rawPdfUrl: string;
  brand: string;
  model: string;
}

export function PDFViewerFrame({ rawPdfUrl, brand, model }: PDFViewerFrameProps) {
  const [isIframeLoading, setIsIframeLoading] = useState(true);

  return (
    <div className="mt-4 pt-4 border-t border-slate-200 h-[600px] w-full relative bg-slate-100 rounded-lg overflow-hidden flex flex-col">
      {isIframeLoading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-100 z-10 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-500" />
          <p className="text-sm font-medium text-slate-500">Trwa ładowanie dokumentu z serwera...</p>
        </div>
      )}
      <object
        data={`${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"}/api/pdf-proxy?url=${encodeURIComponent(rawPdfUrl)}#toolbar=0`}
        type="application/pdf"
        className={cn(
          "w-full h-full border-0 absolute inset-0 transition-opacity duration-300",
          isIframeLoading ? "opacity-0" : "opacity-100"
        )}
        title={`Dokument ${brand} ${model}`}
        onLoad={() => setIsIframeLoading(false)}
      >
        <div className="flex flex-col items-center justify-center p-6 text-center text-slate-500 w-full h-full bg-slate-100 absolute inset-0 z-10">
           <p className="mb-2">Twoja przeglądarka nie obsługuje wbudowanego podglądu PDF pod tym adresem.</p>
           <a href={`${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"}/api/pdf-proxy?url=${encodeURIComponent(rawPdfUrl)}`} target="_blank" rel="noopener noreferrer" className="px-4 py-2 mt-2 bg-blue-600 font-medium text-white rounded-lg shadow-sm hover:bg-blue-700 transition-colors">
             Otwórz dokument w nowej karcie
           </a>
        </div>
      </object>
    </div>
  );
}

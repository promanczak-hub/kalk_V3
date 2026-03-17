import { useState } from "react";
import { UploadCloud } from "lucide-react";
import { cn } from "../../lib/utils";

interface UploadZoneProps {
  onFilesSelected: (files: File[]) => void;
}

export function UploadZone({ onFilesSelected }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFilesSelected(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFilesSelected(Array.from(e.target.files));
    }
  };

  return (
    <div className="w-full mb-6">
      <label
        htmlFor="file-upload"
        className={cn(
          "relative flex flex-col sm:flex-row items-center justify-center w-full py-8 px-10 rounded-xl cursor-pointer transition-all duration-300 ease-in-out group",
          "bg-white/60 backdrop-blur-sm border-2 border-dashed",
          "hover:bg-white/80 hover:shadow-lg hover:shadow-blue-500/5",
          isDragging
            ? "border-blue-400 bg-blue-50/40 shadow-lg shadow-blue-500/10 scale-[1.01]"
            : "border-slate-200/80 hover:border-blue-300",
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="flex items-center gap-5">
          <div className={cn(
            "w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300",
            isDragging
              ? "bg-blue-100 text-blue-600 scale-110"
              : "bg-slate-100 text-slate-400 group-hover:bg-blue-50 group-hover:text-blue-500",
          )}>
            <UploadCloud className="w-6 h-6" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-slate-800">
              Wybierz plik z komputera
            </span>
            <span className="text-xs text-slate-400 font-normal mt-0.5 hidden sm:inline">
              lub przeciągnij go tutaj • PDF, XLS, XLSX do 50 MB
            </span>
          </div>
        </div>
        <div className="mt-3 sm:mt-0 sm:ml-auto">
          <span className={cn(
            "text-[11px] uppercase tracking-wider font-semibold px-3.5 py-1.5 rounded-lg border transition-all duration-300",
            isDragging
              ? "text-blue-600 bg-blue-50 border-blue-200"
              : "text-slate-400 bg-white border-slate-100 group-hover:text-blue-500 group-hover:border-blue-100 group-hover:bg-blue-50/50",
          )}>
            Prześlij pliki
          </span>
        </div>
        <input
          id="file-upload"
          type="file"
          className="hidden"
          multiple
          accept=".pdf,.xls,.xlsx"
          onChange={handleFileSelect}
        />
      </label>
    </div>
  );
}

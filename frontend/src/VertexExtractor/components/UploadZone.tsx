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
    <div className="w-full mb-16">
      <label
        htmlFor="file-upload"
        className={cn(
          "relative flex flex-col sm:flex-row items-center justify-center w-full py-6 px-8 border rounded-lg cursor-pointer transition-all duration-200 ease-in-out group bg-slate-50/50 hover:bg-slate-50",
          isDragging
            ? "border-orange-400 bg-orange-50/30 shadow-inner"
            : "border-slate-200 hover:border-slate-300",
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="flex items-center gap-4">
          <UploadCloud className="w-5 h-5 text-slate-400 group-hover:text-orange-500 transition-colors" />
          <div className="flex flex-col sm:flex-row sm:items-center sm:gap-2">
            <span className="text-sm font-medium text-slate-700">
              Wybierz plik z komputera
            </span>
            <span className="text-sm text-slate-400 font-light hidden sm:inline">
              lub przeciągnij go tutaj
            </span>
          </div>
        </div>
        <div className="mt-2 sm:mt-0 sm:ml-auto">
          <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 bg-white border border-slate-100 px-3 py-1 rounded">
            PDF / XLS / XLSX do 50MB
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

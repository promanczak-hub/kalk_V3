import React, { useRef, useState } from "react";
import { Upload, Loader2 } from "lucide-react";
import axios from "axios";
import { API_BASE_URL } from "../../config/env";

export interface ExtractedServiceOption {
  name: string;
  net_price: number;
  description_or_components: string[];
  effects: {
    override_samar_class?: string;
    override_homologation?: string;
    adds_weight_kg?: number;
    is_financial_only: boolean;
  } | null;
}

export interface ExtractedServiceOptionBatch {
  service_options: ExtractedServiceOption[];
}

type ExtractedServiceOptionResponse =
  | ExtractedServiceOption
  | ExtractedServiceOptionBatch;

interface ServiceOptionsManagerProps {
  onOptionExtracted: (option: ExtractedServiceOption) => void;
}

function isExtractedServiceOptionBatch(
  data: ExtractedServiceOptionResponse
): data is ExtractedServiceOptionBatch {
  return (
    typeof data === "object" &&
    data !== null &&
    "service_options" in data &&
    Array.isArray((data as ExtractedServiceOptionBatch).service_options)
  );
}

function isExtractedServiceOption(
  data: ExtractedServiceOptionResponse
): data is ExtractedServiceOption {
  return (
    typeof data === "object" &&
    data !== null &&
    "name" in data &&
    typeof (data as ExtractedServiceOption).name === "string"
  );
}

function parseNetPrice(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value !== "string") return 0;
  const cleaned = value.replace(/\s+/g, "").replace(/PLN|zł|zl/gi, "").replace(",", ".");
  const numeric = cleaned.match(/-?\d+(?:\.\d+)?/);
  return numeric ? Number(numeric[0]) : 0;
}

function normalizeExtractedOptions(
  data: ExtractedServiceOptionResponse | null | undefined
): ExtractedServiceOption[] {
  if (!data) return [];

  const rows = isExtractedServiceOptionBatch(data)
    ? data.service_options
    : isExtractedServiceOption(data)
      ? [data]
      : [];

  return rows
    .filter((item): item is ExtractedServiceOption => !!item && typeof item.name === "string")
    .map((item) => ({
      ...item,
      net_price: parseNetPrice((item as { net_price?: unknown }).net_price),
    }));
}

export const ServiceOptionsManager: React.FC<ServiceOptionsManagerProps> = ({
  onOptionExtracted,
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setErrorMsg(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post<ExtractedServiceOptionResponse>(
        `${API_BASE_URL}/api/extract/service-option`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      const options = normalizeExtractedOptions(response.data);

      if (options.length === 0) {
        setErrorMsg("Nie znaleziono opcji serwisowych w dokumencie.");
      } else {
        options.forEach(onOptionExtracted);
      }
    } catch (error: unknown) {
      console.error("Error extracting service option:", error);
      let errMsg = "Wystąpił błąd podczas analizy pliku.";
      if (axios.isAxiosError(error) && error.response?.data?.detail) {
        errMsg = error.response.data.detail;
      } else if (error instanceof Error) {
        errMsg = error.message;
      }
      setErrorMsg(errMsg);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div className="p-4 mb-2 border border-dashed border-slate-300 rounded-lg bg-slate-50/50">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-700">
            Dodaj Opcję Serwisową z pliku (Digital Twin)
          </p>
          <p className="text-xs text-slate-400 mt-0.5">
            Wgraj ofertę PDF zabudowy, akcesoriów lub wycenę serwisową.
            AI zinterpretuje koszt, składniki oraz wpływ na homologację.
          </p>
        </div>
        <div className="flex-shrink-0">
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.webp"
            className="hidden"
            ref={fileInputRef}
            onChange={handleFileChange}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="inline-flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-100 disabled:opacity-50 transition-all shadow-sm"
          >
            {isUploading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Upload className="w-3.5 h-3.5" />
            )}
            {isUploading ? "Analizuję..." : "Wgraj i Analizuj"}
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="mt-3 p-2.5 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          {errorMsg}
        </div>
      )}
    </div>
  );
};

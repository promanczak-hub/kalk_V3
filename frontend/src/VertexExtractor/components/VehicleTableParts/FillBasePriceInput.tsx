import { useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { apiClient } from "../../../lib/apiClient";

interface FillBasePriceInputProps {
  vehicleId: string;
  onPriceFilled?: () => void;
}

export function FillBasePriceInput({ vehicleId, onPriceFilled }: FillBasePriceInputProps) {
  const [value, setValue] = useState("");
  const [domain, setDomain] = useState<"brutto" | "netto">("brutto");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parsed = Number(value.replace(/\s/g, "").replace(",", "."));
  const isValid = Number.isFinite(parsed) && parsed > 0;

  const handleSubmit = async (e: React.FormEvent | React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isValid || isSaving) return;
    setIsSaving(true);
    setError(null);
    try {
      const response = await apiClient.fetch(
        `/api/extract/fill-base-price/${vehicleId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ base_price: parsed, domain }),
        }
      );
      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errText}`);
      }
      onPriceFilled?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nieznany błąd");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div
      className="flex flex-col items-end gap-1"
      onClick={(e) => e.stopPropagation()}
    >
      <span
        className="text-[10px] text-amber-600 uppercase tracking-wider font-semibold"
        style={{ fontFamily: "'Geist Mono', monospace" }}
      >
        Wpisz cenę bazową
      </span>
      <div className="flex items-center gap-1.5">
        <input
          type="text"
          inputMode="decimal"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSubmit(e);
          }}
          placeholder="241 000"
          disabled={isSaving}
          className="w-28 px-2 py-1 text-sm font-bold tabular-nums border border-amber-300 rounded text-right focus:outline-none focus:ring-2 focus:ring-amber-400"
          style={{ fontFamily: "'Geist Mono', monospace" }}
        />
        <select
          value={domain}
          onChange={(e) => setDomain(e.target.value as "brutto" | "netto")}
          disabled={isSaving}
          className="text-[10px] font-semibold border border-slate-200 rounded px-1 py-1 bg-white"
          style={{ fontFamily: "'Geist Mono', monospace" }}
        >
          <option value="brutto">BRUTTO</option>
          <option value="netto">NETTO</option>
        </select>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!isValid || isSaving}
          className="bg-amber-500 hover:bg-amber-600 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded p-1 transition-colors"
          title="Zapisz cenę"
        >
          {isSaving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Check className="w-4 h-4" />
          )}
        </button>
      </div>
      {error && (
        <span className="text-[10px] text-red-600 max-w-[200px] text-right">{error}</span>
      )}
    </div>
  );
}

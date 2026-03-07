import { useState, useEffect, useCallback } from "react";

interface ControlCenterData {
  id: number;
  default_wibor: number;
  default_ltr_margin: number;
  default_depreciation_pct: number;
  vat_rate: number;
  bank_spread: number;
  normatywny_przebieg_mc: number;
  resale_time_days: number;
  inventory_financing_cost: number;
  cost_gsm_subscription_monthly: number;
  cost_gsm_device: number;
  cost_gsm_installation: number;
  cost_hook_installation: number;
  cost_grid_dismantling: number;
  cost_registration: number;
  cost_sales_prep: number;
  budzet_marketingowy_ltr: number;
  [key: string]: unknown;
}

interface FieldDef {
  key: keyof ControlCenterData;
  label: string;
  unit?: string;
  step?: string;
  group: string;
}

const FIELDS: FieldDef[] = [
  // Parametry finansowe
  { key: "default_wibor", label: "WIBOR domyślny", unit: "%", step: "0.01", group: "Parametry Finansowe" },
  { key: "bank_spread", label: "Bank Spread (marża finansowa)", unit: "%", step: "0.01", group: "Parametry Finansowe" },
  { key: "default_ltr_margin", label: "Marża sprzedaży LTR", unit: "%", step: "0.1", group: "Parametry Finansowe" },
  // default_depreciation_pct removed — auto-calculated per matrix cell by backend
  { key: "vat_rate", label: "Stawka VAT", unit: "%", step: "1", group: "Parametry Finansowe" },

  // Serwis / Flota
  { key: "normatywny_przebieg_mc", label: "Normatywny przebieg floty", unit: "km/mc", step: "1", group: "Serwis / Flota" },
  { key: "resale_time_days", label: "Czas sprzedaży po kontrakcie", unit: "dni", step: "1", group: "Serwis / Flota" },

  // Koszty dodatkowe
  { key: "cost_gsm_subscription_monthly", label: "GPS — abonament mc", unit: "PLN", step: "1", group: "Koszty Dodatkowe (netto)" },
  { key: "cost_gsm_device", label: "GPS — urządzenie", unit: "PLN", step: "1", group: "Koszty Dodatkowe (netto)" },
  { key: "cost_gsm_installation", label: "GPS — montaż", unit: "PLN", step: "1", group: "Koszty Dodatkowe (netto)" },
  { key: "cost_hook_installation", label: "HAK (koszt legalizacji)", unit: "PLN", step: "1", group: "Koszty Dodatkowe (netto)" },
  { key: "cost_grid_dismantling", label: "Wymontowanie kraty", unit: "PLN", step: "1", group: "Koszty Dodatkowe (netto)" },
  { key: "cost_registration", label: "Rejestracja", unit: "PLN", step: "1", group: "Koszty Dodatkowe (netto)" },
  { key: "cost_sales_prep", label: "Przygotowanie do sprzedaży", unit: "PLN", step: "1", group: "Koszty Dodatkowe (netto)" },
];

export default function GlobalSettingsPanel() {
  const [data, setData] = useState<ControlCenterData | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

  const fetchSettings = useCallback(async () => {
    try {
      const resp = await fetch(`${baseUrl}/api/control-center`);
      if (resp.ok) {
        const json = await resp.json();
        setData(json);
      }
    } catch (e) {
      setError("Nie udało się pobrać ustawień");
      console.error(e);
    }
  }, [baseUrl]);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const handleChange = (key: string, value: string) => {
    if (!data) return;
    const num = parseFloat(value);
    setData({ ...data, [key]: isNaN(num) ? 0 : num });
    setSaved(false);
  };

  const handleSave = async () => {
    if (!data) return;
    setSaving(true);
    setError(null);
    try {
      // Strip non-model fields before sending
      const { id, updated_at, ...payload } = data as ControlCenterData & { updated_at?: string };
      void id; void updated_at;
      const resp = await fetch(`${baseUrl}/api/control-center`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error("Save failed");
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError("Błąd zapisu ustawień");
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  if (!data) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-400">
        <span className="animate-spin mr-2">⏳</span> Ładowanie ustawień...
      </div>
    );
  }

  const groups = [...new Set(FIELDS.map((f) => f.group))];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-800">⚙️ Ustawienia Globalne (Control Center)</h2>
        <button
          onClick={handleSave}
          disabled={saving}
          className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
            saved
              ? "bg-green-500 text-white"
              : "bg-blue-600 hover:bg-blue-700 text-white"
          } disabled:opacity-50`}
        >
          {saving ? "Zapisuję..." : saved ? "✓ Zapisano" : "Zapisz zmiany"}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {groups.map((group) => (
        <div key={group} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">{group}</h3>
          </div>
          <div className="p-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {FIELDS.filter((f) => f.group === group).map((field) => (
              <div key={field.key}>
                <label className="block text-xs font-bold uppercase text-slate-500 mb-1">
                  {field.label}
                </label>
                <div className="flex items-center gap-1">
                  <input
                    type="number"
                    step={field.step || "1"}
                    className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                    value={data[field.key] as number}
                    onChange={(e) => handleChange(String(field.key), e.target.value)}
                  />
                  {field.unit && (
                    <span className="text-xs text-slate-400 whitespace-nowrap">{field.unit}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      <div className="text-xs text-slate-400 text-center">
        Normatywny przebieg: {data.normatywny_przebieg_mc} km/mc = {Math.round(data.normatywny_przebieg_mc * 12)} km/rok
      </div>
    </div>
  );
}

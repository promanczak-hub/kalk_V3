import { useState, useEffect, useCallback } from "react";
import { API_BASE_URL } from "./config/env";
import { supabase } from "./VertexExtractor/lib/supabaseClient";
import { apiClient } from "./lib/apiClient";

interface ControlCenterData {
  id: number;
  default_wibor: number;
  default_ltr_margin: number;
  vat_rate: number;
  bank_spread: number;
  normatywny_przebieg_mc: number;
  resale_time_days: number;
  inventory_financing_cost: number;
  ins_avg_damage_value: number;
  ins_avg_damage_mileage: number;
  cost_gsm_subscription_monthly: number;
  cost_gsm_device: number;
  cost_gsm_installation: number;
  cost_hook_installation: number;
  cost_grid_dismantling: number;
  cost_registration: number;
  cost_sales_prep: number;
  cost_transport: number;
  budzet_marketingowy_ltr: number;
  przewidywana_cena_sprzedazy_lo: number;
  [key: string]: unknown;
}

interface TyreServiceCosts {
  cost_tyre_swap: number;
  cost_tyre_storage: number;
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
  { key: "przewidywana_cena_sprzedazy_lo", label: "Współczynnik WR dla LO", unit: "%", step: "0.01", group: "Parametry Finansowe" },
  { key: "budzet_marketingowy_ltr", label: "Budżet marketingowy LTR", unit: "PLN", step: "1", group: "Parametry Finansowe" },
  // default_depreciation_pct removed — auto-calculated per matrix cell by backend
  { key: "vat_rate", label: "Stawka VAT", unit: "%", step: "1", group: "Parametry Finansowe" },

  // Serwis / Flota
  { key: "normatywny_przebieg_mc", label: "Normatywny przebieg floty", unit: "km/mc", step: "1", group: "Serwis / Flota" },
  { key: "resale_time_days", label: "Czas sprzedaży po kontrakcie", unit: "dni", step: "1", group: "Serwis / Flota" },

  // Ubezpieczenie
  { key: "ins_avg_damage_value", label: "Średnia wartość szkody", unit: "PLN", step: "1", group: "Ubezpieczenie" },
  { key: "ins_avg_damage_mileage", label: "Średni przebieg szkody", unit: "km", step: "1", group: "Ubezpieczenie" },

  // Koszty dodatkowe
  { key: "cost_gsm_subscription_monthly", label: "GPS — abonament mc", unit: "PLN", step: "1", group: "Koszty Dodatkowe (netto)" },
  { key: "cost_gsm_device", label: "GPS — urządzenie", unit: "PLN", step: "1", group: "Koszty Dodatkowe (netto)" },
  { key: "cost_gsm_installation", label: "GPS — montaż", unit: "PLN", step: "1", group: "Koszty Dodatkowe (netto)" },
  { key: "cost_hook_installation", label: "HAK (koszt legalizacji)", unit: "PLN", step: "1", group: "Koszty Dodatkowe (netto)" },
  { key: "cost_grid_dismantling", label: "Wymontowanie kraty", unit: "PLN", step: "1", group: "Koszty Dodatkowe (netto)" },
  { key: "cost_registration", label: "Rejestracja", unit: "PLN", step: "1", group: "Koszty Dodatkowe (netto)" },
  { key: "cost_sales_prep", label: "Przygotowanie do sprzedaży", unit: "PLN", step: "1", group: "Koszty Dodatkowe (netto)" },
  { key: "cost_transport", label: "Opłata transportowa", unit: "PLN", step: "1", group: "Koszty Dodatkowe (netto)" },
];

const DEFAULT_TYRE_SERVICE_COSTS: TyreServiceCosts = {
  cost_tyre_swap: 0,
  cost_tyre_storage: 0,
};

const parseNumberInput = (value: string): number => {
  const parsed = parseFloat(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
};

export default function GlobalSettingsPanel() {
  const [data, setData] = useState<ControlCenterData | null>(null);
  const [tyreServiceCosts, setTyreServiceCosts] = useState<TyreServiceCosts>(DEFAULT_TYRE_SERVICE_COSTS);
  const [loadingTyreServiceCosts, setLoadingTyreServiceCosts] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const baseUrl = API_BASE_URL;

  const fetchSettings = useCallback(async () => {
    try {
      const resp = await apiClient.fetch(`${baseUrl}/api/control-center`);
      if (resp.ok) {
        const json = await resp.json();
        setData(json);
      }
    } catch (e) {
      setError("Nie udało się pobrać ustawień");
      console.error(e);
    }
  }, [baseUrl]);

  const fetchTyreServiceCosts = useCallback(async () => {
    setLoadingTyreServiceCosts(true);
    try {
      const { data: rows, error: queryError } = await supabase
        .from("tyre_configurations")
        .select("config_key, config_value")
        .in("config_key", ["cost_tyre_swap", "cost_tyre_storage"]);
      if (queryError) {
        setError(`Nie udało się pobrać kosztów opon: ${queryError.message}`);
        return;
      }

      const next: TyreServiceCosts = { ...DEFAULT_TYRE_SERVICE_COSTS };
      for (const row of rows ?? []) {
        const key = String(row.config_key ?? "").trim();
        const value = parseNumberInput(String(row.config_value ?? "0"));
        if (key === "cost_tyre_swap") next.cost_tyre_swap = value;
        if (key === "cost_tyre_storage") next.cost_tyre_storage = value;
      }
      setTyreServiceCosts(next);
    } catch (e) {
      setError("Nie udało się pobrać kosztów opon");
      console.error(e);
    } finally {
      setLoadingTyreServiceCosts(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
    fetchTyreServiceCosts();
  }, [fetchSettings, fetchTyreServiceCosts]);

  const handleChange = (key: string, value: string) => {
    if (!data) return;
    const num = parseFloat(value);
    setData({ ...data, [key]: isNaN(num) ? 0 : num });
    setSaved(false);
  };

  const handleTyreCostChange = (key: keyof TyreServiceCosts, value: string) => {
    setTyreServiceCosts((prev) => ({ ...prev, [key]: parseNumberInput(value) }));
    setSaved(false);
  };

  const saveTyreServiceCosts = async () => {
    const payload = [
      {
        config_key: "cost_tyre_swap",
        config_value: String(tyreServiceCosts.cost_tyre_swap),
      },
      {
        config_key: "cost_tyre_storage",
        config_value: String(tyreServiceCosts.cost_tyre_storage),
      },
    ];

    const { error: upsertError } = await supabase
      .from("tyre_configurations")
      .upsert(payload, { onConflict: "config_key" });

    if (upsertError) {
      throw new Error(upsertError.message);
    }
  };

  const handleSave = async () => {
    if (!data) return;
    setSaving(true);
    setError(null);
    try {
      // Strip non-model fields before sending
      const { id, updated_at, ...payload } = data as ControlCenterData & { updated_at?: string };
      void id; void updated_at;

      const resp = await apiClient.fetch(`${baseUrl}/api/control-center`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error("Save failed");

      await saveTyreServiceCosts();

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
        <span className="animate-spin mr-2">...</span> {"Ładowanie ustawień..."}
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

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">Koszty Opon (tyre_configurations)</h3>
          {loadingTyreServiceCosts && <span className="text-xs text-slate-400">Ładowanie...</span>}
        </div>
        <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold uppercase text-slate-500 mb-1">
              Przekładka (za komplet)
            </label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                step="0.01"
                className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                value={tyreServiceCosts.cost_tyre_swap}
                onChange={(e) => handleTyreCostChange("cost_tyre_swap", e.target.value)}
              />
              <span className="text-xs text-slate-400 whitespace-nowrap">PLN netto</span>
            </div>
          </div>
          <div>
            <label className="block text-xs font-bold uppercase text-slate-500 mb-1">
              Przechowywanie (za sezon)
            </label>
            <div className="flex items-center gap-1">
              <input
                type="number"
                step="0.01"
                className="w-full text-xs p-1.5 border border-slate-200 rounded outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                value={tyreServiceCosts.cost_tyre_storage}
                onChange={(e) => handleTyreCostChange("cost_tyre_storage", e.target.value)}
              />
              <span className="text-xs text-slate-400 whitespace-nowrap">PLN netto</span>
            </div>
          </div>
        </div>
      </div>

      <div className="text-xs text-slate-400 text-center">
        Normatywny przebieg: {data.normatywny_przebieg_mc} km/mc = {Math.round(data.normatywny_przebieg_mc * 12)} km/rok
      </div>
    </div>
  );
}

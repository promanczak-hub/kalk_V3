import { create } from 'zustand';
import { apiClient } from "../lib/apiClient";

export interface GlobalSettings {
  cost_gsm_subscription_monthly: number;
  cost_gsm_device: number;
  cost_gsm_installation: number;
  cost_hook_installation: number;
  cost_grid_dismantling: number;
  cost_registration: number;
  cost_sales_prep: number;
  ins_avg_damage_value: number;
  ins_avg_damage_mileage: number;
  car_daily_cost: number;
  cost_marketing_monthly: number;
  normatywny_przebieg_mc: number;
  [key: string]: unknown;
}

interface AppState {
  // ── Global settings ──
  globalSettings: GlobalSettings | null;
  isLoadingSettings: boolean;
  globalError: string | null;
  setGlobalSettings: (settings: GlobalSettings) => void;
  setGlobalError: (err: string | null) => void;

  // ── Settings fetch ──
  fetchGlobalSettings: () => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  // ── Global settings ──
  globalSettings: null,
  isLoadingSettings: false,
  globalError: null,
  setGlobalSettings: (settings) => set({ globalSettings: settings, globalError: null }),
  setGlobalError: (err) => set({ globalError: err }),

  // ── Fetch settings (called once on app init) ──
  fetchGlobalSettings: async () => {
    if (get().globalSettings) return; // already loaded
    set({ isLoadingSettings: true, globalError: null });
    try {
      const res = await apiClient.fetch('/api/control-center');
      if (res.ok) {
        const data = await res.json();
        set({ globalSettings: data, isLoadingSettings: false, globalError: null });
      } else {
        set({ 
          isLoadingSettings: false,
          globalError: 'Krytyczny błąd LTR: Brak odpowiedzi od serwera (Control Center). Mnożniki kalkulatora mogą być niedostępne.'
        });
      }
    } catch {
      set({ 
        isLoadingSettings: false,
        globalError: 'Krytyczny błąd połączenia z bazą: Serwer wyłączony lub nieosiągalny. Kalkulacje biznesowe są zablokowane ze względów bezpieczeństwa.'
      });
    }
  },
}));

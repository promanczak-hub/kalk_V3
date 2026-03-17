import { create } from 'zustand';

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
  setGlobalSettings: (settings: GlobalSettings) => void;


  // ── Settings fetch ──
  fetchGlobalSettings: () => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  // ── Global settings ──
  globalSettings: null,
  isLoadingSettings: false,
  setGlobalSettings: (settings) => set({ globalSettings: settings }),


  // ── Fetch settings (called once on app init) ──
  fetchGlobalSettings: async () => {
    if (get().globalSettings) return; // already loaded
    set({ isLoadingSettings: true });
    try {
      const { apiFetch } = await import('../lib/api');
      const res = await apiFetch('/api/control-center');
      if (res.ok) {
        const data = await res.json();
        set({ globalSettings: data, isLoadingSettings: false });
      } else {
        set({ isLoadingSettings: false });
      }
    } catch {
      set({ isLoadingSettings: false });
    }
  },
}));

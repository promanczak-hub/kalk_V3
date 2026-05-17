import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAppStore, type GlobalSettings } from "./useAppStore";

const makeSettings = (overrides: Partial<GlobalSettings> = {}): GlobalSettings => ({
  cost_gsm_subscription_monthly: 50,
  cost_gsm_device: 200,
  cost_gsm_installation: 100,
  cost_hook_installation: 300,
  cost_grid_dismantling: 50,
  cost_registration: 250,
  cost_sales_prep: 500,
  ins_avg_damage_value: 5000,
  ins_avg_damage_mileage: 80000,
  car_daily_cost: 100,
  cost_marketing_monthly: 200,
  normatywny_przebieg_mc: 2000,
  ...overrides,
});

const resetStore = () => {
  useAppStore.setState({
    globalSettings: null,
    isLoadingSettings: false,
    globalError: null,
  });
};

beforeEach(() => {
  resetStore();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useAppStore", () => {
  describe("setGlobalSettings", () => {
    it("sets settings and clears any prior error", () => {
      useAppStore.setState({ globalError: "stale error" });
      const settings = makeSettings();
      useAppStore.getState().setGlobalSettings(settings);
      expect(useAppStore.getState().globalSettings).toEqual(settings);
      expect(useAppStore.getState().globalError).toBeNull();
    });

    it("overwrites previously set settings", () => {
      useAppStore.getState().setGlobalSettings(makeSettings({ cost_registration: 100 }));
      useAppStore.getState().setGlobalSettings(makeSettings({ cost_registration: 999 }));
      expect(useAppStore.getState().globalSettings?.cost_registration).toBe(999);
    });
  });

  describe("setGlobalError", () => {
    it("sets the error message", () => {
      useAppStore.getState().setGlobalError("connection refused");
      expect(useAppStore.getState().globalError).toBe("connection refused");
    });

    it("clears the error when called with null", () => {
      useAppStore.setState({ globalError: "previous" });
      useAppStore.getState().setGlobalError(null);
      expect(useAppStore.getState().globalError).toBeNull();
    });
  });

  describe("fetchGlobalSettings", () => {
    it("is a no-op when settings are already loaded", async () => {
      const fetchSpy = vi.spyOn(global, "fetch");
      useAppStore.setState({ globalSettings: makeSettings() });

      await useAppStore.getState().fetchGlobalSettings();

      expect(fetchSpy).not.toHaveBeenCalled();
      expect(useAppStore.getState().isLoadingSettings).toBe(false);
    });

    it("populates settings on a 200 response and clears loading", async () => {
      const payload = makeSettings({ cost_registration: 999 });
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify(payload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

      await useAppStore.getState().fetchGlobalSettings();

      expect(useAppStore.getState().globalSettings?.cost_registration).toBe(999);
      expect(useAppStore.getState().isLoadingSettings).toBe(false);
      expect(useAppStore.getState().globalError).toBeNull();
    });

    it("sets globalError when the server returns 500", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify({ detail: "boom" }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        })
      );

      await useAppStore.getState().fetchGlobalSettings();

      expect(useAppStore.getState().globalSettings).toBeNull();
      expect(useAppStore.getState().isLoadingSettings).toBe(false);
      // apiClient throws on !ok → store's catch fires the "połączenia z bazą" message
      expect(useAppStore.getState().globalError).toMatch(/połączenia z bazą|Control Center/);
    });

    it("sets globalError on a network-level rejection", async () => {
      vi.spyOn(global, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));

      await useAppStore.getState().fetchGlobalSettings();

      expect(useAppStore.getState().globalSettings).toBeNull();
      expect(useAppStore.getState().isLoadingSettings).toBe(false);
      expect(useAppStore.getState().globalError).toMatch(/połączenia|wyłączony|nieosiągalny/);
    });

    it("flips isLoadingSettings true while the request is in flight", async () => {
      let resolveFetch: ((value: Response) => void) | undefined;
      const pendingFetch = new Promise<Response>((resolve) => {
        resolveFetch = resolve;
      });
      vi.spyOn(global, "fetch").mockReturnValue(pendingFetch);

      const promise = useAppStore.getState().fetchGlobalSettings();
      // In-flight: isLoadingSettings should be true
      expect(useAppStore.getState().isLoadingSettings).toBe(true);

      resolveFetch?.(
        new Response(JSON.stringify(makeSettings()), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );
      await promise;

      expect(useAppStore.getState().isLoadingSettings).toBe(false);
    });

    it("clears any previously-set globalError when starting a fresh fetch", async () => {
      useAppStore.setState({ globalError: "previous error from somewhere else" });
      const payload = makeSettings();
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify(payload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

      await useAppStore.getState().fetchGlobalSettings();

      expect(useAppStore.getState().globalError).toBeNull();
    });
  });
});

import { useAppStore } from "../stores/useAppStore";

export const API_BASE_URL = import.meta.env.VITE_API_URL || "";
export const DEFAULT_SUPABASE_URL = "https://gnpsdiarmwvqhqbyetce.supabase.co";
export const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || DEFAULT_SUPABASE_URL;
export const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || "";

export function validateEnv(): boolean {
  const errors: string[] = [];

  if (!API_BASE_URL) {
    errors.push("Brak VITE_API_URL w zmiennych środowiskowych.");
  }
  
  if (!SUPABASE_URL) {
    errors.push("Brak SUPABASE_URL w zmiennych środowiskowych.");
  }


  if (!SUPABASE_ANON_KEY) {
    errors.push("Brak VITE_SUPABASE_ANON_KEY w zmiennych środowiskowych.");
  }

  if (errors.length > 0) {
    console.error("Błędy konfiguracji środowiska:", errors);
    useAppStore.getState().setGlobalError("Konfiguracja .env jest niepełna lub błędna: " + errors.join(" "));
    return false;
  }

  return true;
}

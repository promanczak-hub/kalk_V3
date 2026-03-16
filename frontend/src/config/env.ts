export const API_BASE_URL = import.meta.env.VITE_API_URL;
if (!API_BASE_URL) {
  throw new Error("VITE_API_URL is not defined in environment variables.");
}

export const SUPABASE_URL = "https://gnpsdiarmwvqhqbyetce.supabase.co";
const configuredSupabaseUrl = import.meta.env.VITE_SUPABASE_URL;
if (configuredSupabaseUrl && configuredSupabaseUrl !== SUPABASE_URL) {
  throw new Error(
    `Unsupported VITE_SUPABASE_URL: ${configuredSupabaseUrl}. This app is pinned to ${SUPABASE_URL}.`
  );
}

export const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;
if (!SUPABASE_ANON_KEY) {
  throw new Error("VITE_SUPABASE_ANON_KEY is not defined in environment variables.");
}

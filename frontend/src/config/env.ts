export const API_BASE_URL = import.meta.env.VITE_API_URL;
if (!API_BASE_URL) {
  console.error("VITE_API_URL is not defined in environment variables!");
}

export const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
if (!SUPABASE_URL) {
  console.error("VITE_SUPABASE_URL is not defined in environment variables!");
}

export const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;
if (!SUPABASE_ANON_KEY) {
  console.error("VITE_SUPABASE_ANON_KEY is not defined in environment variables!");
}

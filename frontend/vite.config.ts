import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [tailwindcss(), react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/health": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    // Pre-refactor: single 5 MB bundle. Target: split vendor by purpose so
    // each chunk is independently cacheable and the initial route only pulls
    // what it needs. Heavy libs (`react-pdf`, `xlsx`, `ag-grid`) are split
    // by manualChunks AND tree-shaken to their lazy callsites where possible.
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          "react-vendor": ["react", "react-dom", "react-router-dom"],
          "mui-vendor": [
            "@mui/material",
            "@mui/icons-material",
            "@mui/system",
          ],
          "pdf-vendor": ["@react-pdf/renderer", "pdfjs-dist"],
          "grid-vendor": ["ag-grid-community", "ag-grid-react"],
          "chart-vendor": ["recharts"],
          "framer-vendor": ["framer-motion"],
          "supabase-vendor": ["@supabase/supabase-js"],
        },
      },
    },
  },
});

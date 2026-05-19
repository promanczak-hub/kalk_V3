import { useMemo, useEffect, lazy, Suspense } from "react";
import FileUploadOutlinedIcon from "@mui/icons-material/FileUploadOutlined";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";
import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import AdminPanelSettingsOutlinedIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  Tabs,
  Tab,
  Box,
  Typography,
  Alert,
  CircularProgress,
} from "@mui/material";
import {
  Routes,
  Route,
  useNavigate,
  useLocation,
  Navigate,
  Link,
} from "react-router-dom";
import CommandPalette from "./components/CommandPalette";
import { ErrorBoundary } from "./components/ErrorBoundary";

import { NotificationProvider } from "./components/NotificationProvider";
import { useAppStore } from "./stores/useAppStore";
import OfferCartFab from "./components/OfferCart/OfferCartFab";

// Lazy-load route components to split the initial bundle. Each page lives
// in its own chunk and only downloads when the user navigates to it.
// Pre-refactor: single 5.0 MB bundle. Target: 1.5–2 MB initial + per-route chunks.
const VertexExtractorPage = lazy(
  () => import("./VertexExtractor/VertexExtractorPage"),
);
const ScoringSearchPage = lazy(() =>
  import("./ScoringSearch/ScoringSearchPage").then((m) => ({
    default: m.ScoringSearchPage,
  })),
);
const CalculationsHistoryPage = lazy(() =>
  import("./CalculationsHistory/CalculationsHistoryPage").then((m) => ({
    default: m.CalculationsHistoryPage,
  })),
);
const PipelineMapPage = lazy(() => import("./PipelineMap/PipelineMapPage"));

function RouteFallback() {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", py: 10 }}>
      <CircularProgress size={32} />
      <Typography variant="body2" sx={{ ml: 2, color: "text.secondary" }}>
        Ładowanie sekcji…
      </Typography>
    </Box>
  );
}

/**
 * Route definitions — single source of truth for navigation.
 *
 * `external: true` oznacza link otwierany w nowej karcie (Supabase
 * Dashboard pod osobnym hostem). External routes są wyświetlane jako
 * MUI <Tab component="a"> i NIE są częścią <Routes>.
 */
const ADMIN_URL =
  (import.meta.env.VITE_ADMIN_URL as string | undefined) || "";

const ROUTES = [
  { path: "/", label: "Ekstrakcja i Analiza AI", icon: <FileUploadOutlinedIcon fontSize="small" />, external: false },
  { path: "/search", label: "Szukaj Ofert", icon: <SearchOutlinedIcon fontSize="small" />, external: false },
  { path: "/calculations", label: "Historia Kalkulacji", icon: <HistoryOutlinedIcon fontSize="small" />, external: false },
  { path: "/pipeline-map", label: "Mapa Pipeline", icon: <AccountTreeOutlinedIcon fontSize="small" />, external: false },
  ...(ADMIN_URL
    ? [{
        path: ADMIN_URL,
        label: "Panel admin",
        icon: <AdminPanelSettingsOutlinedIcon fontSize="small" />,
        external: true as const,
      }]
    : []),
] as const;

interface AppContentProps {
  mode: "light" | "dark";
}

function AppContent({ mode }: AppContentProps) {
  const navigate = useNavigate();
  const location = useLocation();

  // External (Supabase Dashboard) nie matchuje location.pathname, więc activeTab
  // odpowiada tylko wewnętrznym routes.
  const currentTabIndex = ROUTES.findIndex(
    (r) => !r.external && r.path === location.pathname
  );
  const activeTab = currentTabIndex >= 0 ? currentTabIndex : 0;

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    const route = ROUTES[newValue];
    if (!route) return;
    if (route.external) {
      // Otwórz w nowej karcie — nie zmieniaj activeTab w głównym oknie.
      window.open(route.path, "_blank", "noopener,noreferrer");
      return;
    }
    navigate(route.path);
  };

  // Listen for global tab switch events (backward compat)
  useEffect(() => {
    const handleSwitchTab = (event: CustomEvent<{ tabIndex: number }>) => {
      const route = ROUTES[event.detail.tabIndex];
      if (!route || route.external) return;
      navigate(route.path);
    };

    window.addEventListener('switchTab', handleSwitchTab as EventListener);
    return () => {
      window.removeEventListener('switchTab', handleSwitchTab as EventListener);
    };
  }, [navigate]);

  // Fetch global settings on mount
  const fetchGlobalSettings = useAppStore((s) => s.fetchGlobalSettings);
  const globalError = useAppStore((s) => s.globalError);
  
  useEffect(() => {
    import("./config/env").then(({ validateEnv }) => {
      validateEnv();
    });
    fetchGlobalSettings();
  }, [fetchGlobalSettings]);

  return (
    <div style={{ minHeight: "100vh" }}>
      {/* ── Sticky Header ── */}
      <Box
        component="header"
        sx={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          zIndex: 1100,
          backdropFilter: "blur(12px)",
          backgroundColor: mode === "light" ? "rgba(255,255,255,0.85)" : "rgba(10, 15, 30, 0.85)",
          borderBottom: "1px solid",
          borderColor: mode === "light" ? "rgba(0,0,0,0.08)" : "rgba(255,255,255,0.08)",
          boxShadow: mode === "light" ? "0 1px 3px rgba(0,0,0,0.04)" : "0 4px 12px rgba(0,0,0,0.2)",
          px: { xs: 2, md: 4 },
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 2,
            maxWidth: 1920,
            mx: "auto",
            height: 56,
          }}
        >
          {/* Logo */}
          <Link to="/" style={{ display: 'flex', alignItems: 'center' }}>
            <img
              src="/express-logo.png"
              alt="Express Car Rental"
              style={{ height: 30, flexShrink: 0 }}
            />
          </Link>

          {/* Separator */}
          <Box sx={{ width: "1px", height: 24, bgcolor: "divider", flexShrink: 0 }} />

          {/* Navigation Tabs */}
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            indicatorColor="primary"
            textColor="primary"
            variant="scrollable"
            scrollButtons="auto"
            aria-label="Nawigacja"
            sx={{
              flexGrow: 1,
              minHeight: 56,
              "& .MuiTab-root": {
                minHeight: 56,
                fontWeight: 500,
                fontSize: "0.85rem",
                textTransform: "none",
                letterSpacing: "0.01em",
              },
            }}
          >
            {ROUTES.map((route) => (
              <Tab
                key={route.path}
                label={
                  route.external ? (
                    <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
                      {route.label}
                      <OpenInNewIcon sx={{ fontSize: 12, opacity: 0.7 }} />
                    </Box>
                  ) : (
                    route.label
                  )
                }
                icon={route.icon}
                iconPosition="start"
              />
            ))}
          </Tabs>

            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 1.5,
              flexShrink: 0,
              ml: 'auto' // Push to right
            }}>



              {/* Keyboard shortcut hint */}
              <Box
                sx={{
                  display: { xs: "none", md: "flex" },
                  alignItems: "center",
                  gap: 0.5,
                  px: 1.5,
                  py: 0.5,
                  borderRadius: "6px",
                  border: "1px solid",
                  borderColor: mode === "light" ? "rgba(0,0,0,0.08)" : "rgba(255,255,255,0.15)",
                  bgcolor: mode === "light" ? "rgba(0,0,0,0.02)" : "rgba(255,255,255,0.05)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  "&:hover": {
                    bgcolor: mode === "light" ? "rgba(0,0,0,0.05)" : "rgba(255,255,255,0.08)",
                    borderColor: mode === "light" ? "rgba(0,0,0,0.15)" : "rgba(255,255,255,0.25)",
                  },
                }}
                onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }))}
              >
                <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.72rem", fontWeight: 500 }}>
                  Ctrl+K
                </Typography>
              </Box>
            </Box>
          </Box>
      </Box>

      {/* ── Global Error Banner ── */}
      {globalError && (
        <Box sx={{ position: "fixed", top: 56, left: 0, right: 0, zIndex: 1099 }}>
          <Alert severity="error" variant="filled" sx={{ borderRadius: 0, justifyContent: 'center', fontWeight: 600 }}>
            {globalError}
          </Alert>
        </Box>
      )}

      {/* ── Main Content ── */}
      <Box sx={{ px: { xs: 2, md: 4 }, pb: 3, pt: globalError ? "112px" : "80px", maxWidth: 1920, mx: "auto", transition: 'padding-top 0.2s ease' }}>
        <ErrorBoundary fallbackTitle="Błąd ładowania sekcji">
          <Suspense fallback={<RouteFallback />}>
            <Routes>
              <Route path="/" element={<VertexExtractorPage />} />
              <Route path="/calculations" element={<CalculationsHistoryPage />} />
              <Route path="/search" element={<ScoringSearchPage />} />
              <Route path="/pipeline-map" element={<PipelineMapPage />} />

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </Box>
    </div>
  );
}

function App() {
  const mode: "light" | "dark" = "light";

  const theme = useMemo(() => createTheme({
    palette: {
      mode,
      primary: {
        main: mode === "light" ? "#1e3a8a" : "#3b82f6",
      },
      background: {
        default: mode === "light" ? "#ffffff" : "#0f172a",
        paper: mode === "light" ? "#ffffff" : "#1e293b",
      },
      divider: mode === "light" ? "rgba(0,0,0,0.12)" : "rgba(255,255,255,0.12)",
    },
    typography: {
      fontFamily:
        '"Geist", "Segoe UI", "Roboto", "Helvetica", "Arial", sans-serif',
      fontSize: 14,
      h5: { fontWeight: 700, letterSpacing: "-0.01em" },
      h6: { fontWeight: 600, fontSize: "1.05rem", letterSpacing: "-0.01em" },
      subtitle1: { fontWeight: 600, fontSize: "0.9rem" },
      subtitle2: { fontWeight: 600, fontSize: "0.8rem", letterSpacing: "0.02em", textTransform: "uppercase" as const, color: "#64748b" },
      body2: { fontSize: "0.85rem" },
    },
    components: {
      MuiTextField: {
        defaultProps: {
          size: "small",
          variant: "outlined",
        },
      },
      MuiSelect: {
        defaultProps: {
          size: "small",
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: "none",
            boxShadow: "none",
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            fontWeight: 500,
            fontSize: "0.75rem",
            borderRadius: "6px",
            transition: "all 0.15s ease",
            "&:hover": {
              transform: "translateY(-1px)",
              boxShadow: "0 2px 4px rgba(0,0,0,0.08)",
            },
          },
          sizeSmall: {
            height: 24,
            fontSize: "0.72rem",
          },
        },
      },
      MuiAccordionSummary: {
        styleOverrides: {
          root: {
            background: "linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)",
            color: "#ffffff",
            minHeight: "40px !important",
            "& .MuiAccordionSummary-content": {
              margin: "8px 0 !important",
            },
            "& .MuiSvgIcon-root": {
              color: "#ffffff",
            },
          },
        },
      },
      MuiAccordionDetails: {
        styleOverrides: {
          root: {
            padding: "16px 24px",
            border: "1px solid #e0e0e0",
            borderTop: "none",
          },
        },
      },
      MuiAccordion: {
        styleOverrides: {
          root: {
            boxShadow: "none",
            "&:before": {
              display: "none",
            },
            marginBottom: "16px",
            backgroundColor: mode === 'light' ? "#ffffff" : "#1e293b",
            color: mode === 'light' ? "inherit" : "#f1f5f9",
          },
        },
      },
    },
  }), [mode]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <NotificationProvider>
        <ErrorBoundary fallbackTitle="Krytyczny błąd aplikacji">
          <CommandPalette />
          <OfferCartFab />
          <AppContent mode={mode} />
        </ErrorBoundary>
      </NotificationProvider>
    </ThemeProvider>
  );
}

export default App;

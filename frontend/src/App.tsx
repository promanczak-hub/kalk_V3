import { useMemo, useEffect } from "react";
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  Tabs,
  Tab,
  Box,
} from "@mui/material";
import {
  Routes,
  Route,
  useNavigate,
  useLocation,
  Navigate,
} from "react-router-dom";
import ControlCenter from "./ControlCenter";
import VertexExtractorPage from "./VertexExtractor/VertexExtractorPage";
import CommandPalette from "./components/CommandPalette";
import { CatalogLibraryPage } from "./VertexExtractor/components/CatalogLibraryPage";
import { ScoringSearchPage } from "./ScoringSearch/ScoringSearchPage";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { NotificationProvider } from "./components/NotificationProvider";
import { useAppStore } from "./stores/useAppStore";

/**
 * Route definitions — single source of truth for navigation.
 */
const ROUTES = [
  { path: "/", label: "Ekstrakcja Danych" },
  { path: "/control-center", label: "Control Center" },
  { path: "/library", label: "Biblioteka Cenników" },
  { path: "/search", label: "Wyszukiwarka pojazdów" },
] as const;

function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();

  const currentTabIndex = ROUTES.findIndex(
    (r) => r.path === location.pathname
  );
  const activeTab = currentTabIndex >= 0 ? currentTabIndex : 0;

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    navigate(ROUTES[newValue].path);
  };

  // Listen for global tab switch events (backward compat)
  useEffect(() => {
    const handleSwitchTab = (event: CustomEvent<{ tabIndex: number }>) => {
      const route = ROUTES[event.detail.tabIndex];
      if (route) navigate(route.path);
    };

    window.addEventListener('switchTab', handleSwitchTab as EventListener);
    return () => {
      window.removeEventListener('switchTab', handleSwitchTab as EventListener);
    };
  }, [navigate]);

  // Fetch global settings on mount
  const fetchGlobalSettings = useAppStore((s) => s.fetchGlobalSettings);
  useEffect(() => {
    fetchGlobalSettings();
  }, [fetchGlobalSettings]);

  return (
    <div
      style={{
        minHeight: "100vh",
        padding: "24px 32px",
      }}
    >
      {/* Express Car Rental Logo */}
      <Box sx={{ mb: 2 }}>
        <img src="/express-logo.png" alt="Express Car Rental" style={{ height: 40 }} />
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="scrollable"
          scrollButtons="auto"
          aria-label="Nawigacja"
        >
          {ROUTES.map((route) => (
            <Tab key={route.path} label={route.label} />
          ))}
        </Tabs>
      </Box>

      <ErrorBoundary fallbackTitle="Błąd ładowania sekcji">
        <Routes>
          <Route path="/" element={<VertexExtractorPage />} />
          <Route path="/control-center" element={<ControlCenter />} />
          <Route path="/library" element={<CatalogLibraryPage />} />
          <Route path="/search" element={<ScoringSearchPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </ErrorBoundary>
    </div>
  );
}

function App() {
  const mode = useAppStore((s) => s.themeMode);
  const toggleTheme = useAppStore((s) => s.toggleTheme);

  const theme = useMemo(() => createTheme({
    palette: {
      mode,
      primary: {
        main: mode === 'light' ? "#1e3a8a" : "#90caf9",
      },
      background: {
        default: mode === 'light' ? "#ffffff" : "#121212",
        paper: mode === 'light' ? "#ffffff" : "#1e1e1e",
      },
    },
    typography: {
      fontFamily:
        '"Geist", "Segoe UI", "Roboto", "Helvetica", "Arial", sans-serif',
      fontSize: 13,
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
      MuiAccordionSummary: {
        styleOverrides: {
          root: {
            backgroundColor: mode === 'light' ? "#1e3a8a" : "#2d2d2d",
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
            border: `1px solid ${mode === 'light' ? '#e0e0e0' : '#444'}`,
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
            backgroundColor: mode === 'light' ? "#ffffff" : "#1e1e1e",
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
          <CommandPalette toggleTheme={toggleTheme} mode={mode} />
          <AppContent />
        </ErrorBoundary>
      </NotificationProvider>
    </ThemeProvider>
  );
}

export default App;

import { useState, useEffect, useMemo } from "react";
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  Tabs,
  Tab,
  Box,
} from "@mui/material";
import CalculatorPanel from "./CalculatorPanel";
import ControlCenter from "./ControlCenter";
import KalkulacjeList from "./KalkulacjeList";
import VertexExtractorPage from "./VertexExtractor/VertexExtractorPage";
import CommandPalette from "./components/CommandPalette";
import { ReverseSearchPage } from "./VertexExtractor/components/ReverseSearchPage";

function App() {
  const [mode, setMode] = useState<'light' | 'dark'>('light');

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
  const [currentTab, setCurrentTab] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('id') ? 2 : 0;
  });

  const [editingTitle, setEditingTitle] = useState<string | null>(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('kalkulacja') || (params.get('id') ? `ID: ${params.get('id')}` : null);
  });

  // Remove useEffect for tab switching


  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
    if (newValue === 1 || newValue === 0) {
      window.history.replaceState({}, "", "/"); // Wyczyść URL jeśli wracasz do listy
      setEditingTitle(null);
    }
  };

  // Listen for global tab switch events
  useEffect(() => {
    const handleSwitchTab = (event: CustomEvent<{ tabIndex: number; urlParams?: URLSearchParams }>) => {
      setCurrentTab(event.detail.tabIndex);
      if (event.detail.urlParams) {
        window.history.pushState({}, "", `/?${event.detail.urlParams.toString()}`);
        if (event.detail.tabIndex === 2) {
          setEditingTitle(event.detail.urlParams.get('kalkulacja') || `ID: ${event.detail.urlParams.get('id')}`);
        }
      }
    };

    window.addEventListener('switchTab', handleSwitchTab as EventListener);
    return () => {
      window.removeEventListener('switchTab', handleSwitchTab as EventListener);
    };
  }, []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <CommandPalette toggleTheme={() => setMode(m => m === 'light' ? 'dark' : 'light')} mode={mode} />
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
            value={currentTab}
            onChange={handleTabChange}
            indicatorColor="primary"
            textColor="primary"
            variant="scrollable"
            scrollButtons="auto"
            aria-label="Nawigacja"
          >
            <Tab value={0} label="Ekstrakcja Danych" />
            <Tab value={1} label="Kalkulacje" />
            <Tab 
              value={2} 
              label={editingTitle ? `Kalkulacja: ${editingTitle}` : "Edytor"} 
              sx={{ display: editingTitle ? 'flex' : 'none' }} 
            />
            <Tab value={3} label="Control Center" />
            <Tab value={4} label="Reverse Search" />
          </Tabs>
        </Box>

        {currentTab === 0 && <VertexExtractorPage />}
        {currentTab === 1 && <KalkulacjeList />}
        {currentTab === 2 && <CalculatorPanel />}
        {currentTab === 3 && <ControlCenter />}
        {currentTab === 4 && <ReverseSearchPage />}
      </div>
    </ThemeProvider>
  );
}

export default App;

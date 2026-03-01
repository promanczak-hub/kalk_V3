import { useState, useEffect } from "react";
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

const lightTheme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#1e3a8a", // Ciemny niebieski widziany w nagłówkach
    },
    background: {
      default: "#ffffff",
      paper: "#ffffff",
    },
  },
  typography: {
    fontFamily:
      '"Inter", "Segoe UI", "Roboto", "Helvetica", "Arial", sans-serif',
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
          backgroundColor: "#1e3a8a",
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
        },
      },
    },
  },
});

function App() {
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
    <ThemeProvider theme={lightTheme}>
      <CssBaseline />
      <div
        style={{
          minHeight: "100vh",
          padding: "24px",
          maxWidth: "1400px",
          margin: "0 auto",
        }}
      >
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
            <Tab value={0} label="Vertex Extractor" />
            <Tab value={1} label="Kalkulacje" />
            <Tab 
              value={2} 
              label={editingTitle ? `Kalkulacja: ${editingTitle}` : "Edytor"} 
              sx={{ display: editingTitle ? 'flex' : 'none' }} 
            />
            <Tab value={3} label="Control Center (Parametry Globalne)" />
          </Tabs>
        </Box>

        {currentTab === 0 && <VertexExtractorPage />}
        {currentTab === 1 && <KalkulacjeList />}
        {currentTab === 2 && <CalculatorPanel />}
        {currentTab === 3 && <ControlCenter />}
      </div>
    </ThemeProvider>
  );
}

export default App;

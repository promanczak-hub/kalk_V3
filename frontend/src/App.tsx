import { useState } from 'react';
import { ThemeProvider, createTheme, CssBaseline, Tabs, Tab, Box } from '@mui/material';
import CalculatorPanel from './CalculatorPanel';
import ControlCenter from './ControlCenter';

const lightTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1e3a8a', // Ciemny niebieski widziany w nagłówkach
    },
    background: {
      default: '#ffffff',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: '"Inter", "Segoe UI", "Roboto", "Helvetica", "Arial", sans-serif',
    fontSize: 13,
  },
  components: {
    MuiTextField: {
      defaultProps: {
        size: 'small',
        variant: 'outlined',
      }
    },
    MuiSelect: {
      defaultProps: {
        size: 'small',
      }
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          boxShadow: 'none',
        }
      }
    },
    MuiAccordionSummary: {
      styleOverrides: {
        root: {
          backgroundColor: '#1e3a8a',
          color: '#ffffff',
          minHeight: '40px !important',
          '& .MuiAccordionSummary-content': {
            margin: '8px 0 !important',
          },
          '& .MuiSvgIcon-root': {
            color: '#ffffff',
          }
        }
      }
    },
    MuiAccordionDetails: {
      styleOverrides: {
        root: {
          padding: '16px 24px',
          border: '1px solid #e0e0e0',
          borderTop: 'none',
        }
      }
    },
    MuiAccordion: {
      styleOverrides: {
        root: {
          boxShadow: 'none',
          '&:before': {
            display: 'none',
          },
          marginBottom: '16px',
        }
      }
    }
  }
});

function App() {
  const [currentTab, setCurrentTab] = useState(0);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  return (
    <ThemeProvider theme={lightTheme}>
      <CssBaseline />
      <div style={{ minHeight: '100vh', padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
        
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
          <Tabs value={currentTab} onChange={handleTabChange} indicatorColor="primary" textColor="primary" aria-label="Nawigacja">
            <Tab label="Kalkulator LTR (Matrix)" />
            <Tab label="Control Center (Parametry Globalne)" />
          </Tabs>
        </Box>

        {currentTab === 0 && <CalculatorPanel />}
        {currentTab === 1 && <ControlCenter />}

      </div>
    </ThemeProvider>
  );
}

export default App;

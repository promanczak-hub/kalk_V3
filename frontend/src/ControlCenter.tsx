import { useState } from "react";
import { Box, Tabs, Tab, Paper, Typography, Divider } from "@mui/material";
import GlobalSettingsPanel from "./GlobalSettingsPanel";
import ExcelDraftsPanel from "./ExcelDrafts/ExcelDraftsPanel";

// Imports from DaneZaleznePage
import SamarMasterPanel from "./SamarMasterPanel";
import EnginesCrudPanel from "./EnginesCrud/EnginesCrudPanel";
import TabelaOponCrudPanel from "./TabelaOponCrud/TabelaOponCrudPanel";
import TransportFeesPanel from "./TransportFeesCrud/TransportFeesPanel";
import RabatyCrudPanel from "./RabatyCrud/RabatyCrudPanel";
import TabOkresFinalCrudPanel from "./TabOkresFinal/TabOkresFinalCrudPanel";
import MileageAdjustmentsCrudPanel from "./MileageAdjustmentsCrud/MileageAdjustmentsCrudPanel";
import BrandCorrectionCrudPanel from "./BrandCorrectionCrud/BrandCorrectionCrudPanel";
import ServiceCostsCrudPanel from "./ServiceCostsCrud/ServiceCostsCrudPanel";
import ReplacementCarCrudPanel from "./ReplacementCarCrud/ReplacementCarCrudPanel";
import InsuranceRatesCrudPanel from "./InsuranceRatesCrud/InsuranceRatesCrudPanel";
import DamageCoefficientsCrudPanel from "./DamageCoefficientsCrud/DamageCoefficientsCrudPanel";
import DatabaseRegistryPanel from "./ControlCenter/DatabaseRegistryPanel";

const CONFIG_TABS = [
  { group: "Audyt i Rejestr", label: "🗄️ Rejestr Baz Danych (Audit)", render: () => <DatabaseRegistryPanel /> },
  { group: "Baza Główna", label: "🗂️ Klasy SAMAR (Master)", render: () => <SamarMasterPanel /> },
  { group: "Baza Główna", label: "🏎️ Tabele Napędów", render: () => <EnginesCrudPanel /> },
  { group: "Wartości Rezydualne", label: "📉 TAB. OKRES FINAL", render: () => <TabOkresFinalCrudPanel /> },
  { group: "Wartości Rezydualne", label: "🛣️ Korekty Przebiegowe", render: () => <MileageAdjustmentsCrudPanel /> },
  { group: "Wartości Rezydualne", label: "🏢 Korekty Marki/Modelu", render: () => <BrandCorrectionCrudPanel /> },
  { group: "Koszty Eksploatacji", label: "🛠️ Koszty Serwisu", render: () => <ServiceCostsCrudPanel /> },
  { group: "Koszty Eksploatacji", label: "🛞 Tabela Opon", render: () => <TabelaOponCrudPanel /> },
  { group: "Koszty Eksploatacji", label: "🚗 Auto Zastępcze", render: () => <ReplacementCarCrudPanel /> },
  { group: "Ubezpieczenia i Ryzyko", label: "🛡️ Stawki AC/OC", render: () => <InsuranceRatesCrudPanel /> },
  { group: "Ubezpieczenia i Ryzyko", label: "💥 Współczynniki Szkodowe", render: () => <DamageCoefficientsCrudPanel /> },
  { group: "Koszty Zakupu", label: "🚚 Opłaty Transportowe", render: () => <TransportFeesPanel /> },
  { group: "Koszty Zakupu", label: "💰 Tabele Rabatów", render: () => <RabatyCrudPanel /> }
];

export default function ControlCenter() {
  const [activeMainTab, setActiveMainTab] = useState(0);
  const [activeConfigTab, setActiveConfigTab] = useState(0);

  return (
    <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 3, minHeight: 'calc(100vh - 120px)' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs
          value={activeMainTab}
          onChange={(_e, val) => setActiveMainTab(val)}
          indicatorColor="primary"
          textColor="primary"
          sx={{
            minHeight: 48,
            "& .MuiTab-root": {
              textTransform: "none",
              fontWeight: 600,
              fontSize: "0.9rem",
              px: 3,
            },
          }}
        >
          <Tab label="⚙️ Główne Parametry" />
          <Tab label="📝 Modele Wyceny (Draft)" />
          <Tab label="📊 Bazy Danych i Konfiguracja" />
        </Tabs>
      </Box>

      {activeMainTab === 0 && (
        <Box sx={{ mt: 1 }}>
          <GlobalSettingsPanel />
        </Box>
      )}

      {activeMainTab === 1 && (
        <Box sx={{ mt: 1 }}>
          <ExcelDraftsPanel />
        </Box>
      )}

      {activeMainTab === 2 && (
        <Box sx={{ display: "flex", gap: 3, height: 'calc(100vh - 200px)' }}>
          {/* Sidebar Navigation */}
          <Paper elevation={0} sx={{ 
            width: 260, 
            flexShrink: 0, 
            display: 'flex', 
            flexDirection: 'column', 
            overflowY: 'auto',
            borderRadius: 2,
            border: 1,
            borderColor: 'divider',
            bgcolor: 'grey.50'
          }}>
            <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
              <Typography variant="overline" color="text.secondary" fontWeight="bold">Podkategorie</Typography>
            </Box>
            <Tabs
              orientation="vertical"
              variant="scrollable"
              value={activeConfigTab}
              onChange={(_e, val) => setActiveConfigTab(val)}
              sx={{
                flexGrow: 1,
                '& .MuiTabs-indicator': { left: 0, width: 3 },
                '& .MuiTab-root': {
                  alignItems: 'flex-start',
                  textAlign: 'left',
                  textTransform: 'none',
                  minHeight: 40,
                  py: 1,
                  px: 2,
                  justifyContent: 'flex-start',
                  fontSize: '0.8rem',
                  fontWeight: 500,
                  color: 'text.secondary',
                  '&.Mui-selected': {
                    color: 'primary.main',
                    fontWeight: 700,
                    bgcolor: 'white'
                  },
                  '&:hover': {
                    bgcolor: 'rgba(0,0,0,0.02)'
                  }
                }
              }}
            >
              {CONFIG_TABS.map((t, i) => (
                <Tab key={i} label={t.label} />
              ))}
            </Tabs>
          </Paper>

          {/* Configuration Panel Content */}
          <Box sx={{ flexGrow: 1, overflowY: 'auto', pr: 1 }}>
            <Paper elevation={0} sx={{ p: 3, borderRadius: 2, border: 1, borderColor: 'divider', minHeight: '100%' }}>
              <Box sx={{ mb: 3 }}>
                <Typography variant="h6" color="primary.main" gutterBottom>
                  {CONFIG_TABS[activeConfigTab].label}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Grupa: {CONFIG_TABS[activeConfigTab].group}
                </Typography>
                <Divider sx={{ mt: 2 }} />
              </Box>
              {CONFIG_TABS[activeConfigTab].render()}
            </Paper>
          </Box>
        </Box>
      )}
    </Box>
  );
}

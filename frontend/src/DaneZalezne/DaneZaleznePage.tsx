import { useState } from "react";
import { Box, Tabs, Tab, Typography, Paper } from "@mui/material";

import SamarMasterPanel from "../SamarMasterPanel";
import EnginesCrudPanel from "../EnginesCrud/EnginesCrudPanel";
import TabelaOponCrudPanel from "../TabelaOponCrud/TabelaOponCrudPanel";
import TransportFeesPanel from "../TransportFeesCrud/TransportFeesPanel";
import RabatyCrudPanel from "../RabatyCrud/RabatyCrudPanel";

import TabOkresFinalCrudPanel from "../TabOkresFinal/TabOkresFinalCrudPanel";
import MileageAdjustmentsCrudPanel from "../MileageAdjustmentsCrud/MileageAdjustmentsCrudPanel";
import BrandCorrectionCrudPanel from "../BrandCorrectionCrud/BrandCorrectionCrudPanel";
import ServiceCostsCrudPanel from "../ServiceCostsCrud/ServiceCostsCrudPanel";
import ReplacementCarCrudPanel from "../ReplacementCarCrud/ReplacementCarCrudPanel";
import InsuranceRatesCrudPanel from "../InsuranceRatesCrud/InsuranceRatesCrudPanel";
import DamageCoefficientsCrudPanel from "../DamageCoefficientsCrud/DamageCoefficientsCrudPanel";

const TABS: { group: string; label: string; render: () => React.ReactNode }[] = [
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

export function DaneZaleznePage() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <Box sx={{ p: { xs: 1, md: 2 }, display: "flex", gap: 3, height: 'calc(100vh - 100px)' }}>
      {/* Sidebar Navigation */}
      <Paper elevation={1} sx={{ 
        width: 280, 
        flexShrink: 0, 
        display: 'flex', 
        flexDirection: 'column', 
        overflowY: 'auto',
        borderRadius: 2,
        border: 1,
        borderColor: 'divider'
      }}>
        <Box sx={{ p: 2, bgcolor: 'primary.main', color: 'primary.contrastText', position: 'sticky', top: 0, zIndex: 10 }}>
          <Typography variant="subtitle1" fontWeight="bold">Dane Zależne</Typography>
          <Typography variant="caption" sx={{ opacity: 0.8 }}>Zastępuje arkusz Google Sheets</Typography>
        </Box>
        <Tabs
          orientation="vertical"
          variant="scrollable"
          value={activeTab}
          onChange={(_e, val) => setActiveTab(val)}
          sx={{
            flexGrow: 1,
            '& .MuiTabs-indicator': { left: 0, width: 4, borderRadius: '0 4px 4px 0' },
            '& .MuiTab-root': {
              alignItems: 'flex-start',
              textAlign: 'left',
              textTransform: 'none',
              minHeight: 48,
              py: 1.5,
              px: 2.5,
              justifyContent: 'flex-start',
              fontSize: '0.85rem',
              fontWeight: 500,
              color: 'text.secondary',
              borderBottom: '1px solid',
              borderBottomColor: 'divider',
              '&.Mui-selected': {
                color: 'primary.main',
                fontWeight: 700,
                bgcolor: 'action.selected'
              }
            }
          }}
        >
          {TABS.map((t, i) => (
            <Tab key={i} label={t.label} />
          ))}
        </Tabs>
      </Paper>

      {/* Main Content Area */}
      <Box sx={{ flexGrow: 1, overflowY: 'auto', pr: 1, display: 'flex', flexDirection: 'column' }}>
        {TABS[activeTab].render()}
      </Box>
    </Box>
  );
}

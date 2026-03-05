import { useState } from "react";
import { Box, Tabs, Tab } from "@mui/material";
import RmsCrudPanel from "./RmsCrud/RmsCrudPanel";
import RabatyCrudPanel from "./RabatyCrud/RabatyCrudPanel";
import EnginesCrudPanel from "./EnginesCrud/EnginesCrudPanel";
import ServiceCostsCrudPanel from "./ServiceCostsCrud/ServiceCostsCrudPanel";
import TabelaOponCrudPanel from "./TabelaOponCrud/TabelaOponCrudPanel";
import BrandCorrectionCrudPanel from "./BrandCorrectionCrud/BrandCorrectionCrudPanel";
import ReplacementCarCrudPanel from "./ReplacementCarCrud/ReplacementCarCrudPanel";
import GlobalSettingsPanel from "./GlobalSettingsPanel";
import DepreciationRatesPanel from "./DepreciationRatesCrud/DepreciationRatesPanel";
import MileageCorrectionsPanel from "./MileageCorrectionsCrud/MileageCorrectionsPanel";

export default function ControlCenter() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 3 }}>
      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
        <Tabs value={activeTab} onChange={(_e, val) => setActiveTab(val)} variant="scrollable" scrollButtons="auto">
          <Tab label="Ustawienia Globalne" />
          <Tab label="Tabele RMS _czak" />
          <Tab label="Tabela rabaty" />
          <Tab label="Tabele Napędy" />
          <Tab label="Krzywe Deprecjacji" />
          <Tab label="Korekty Przebiegowe" />
          <Tab label="Koszty Serwisowe" />
          <Tab label="Tabela Opon" />
          <Tab label="Korekta Marka" />
          <Tab label="Samochód Zastępczy" />
        </Tabs>
      </Box>

      {activeTab === 0 && <GlobalSettingsPanel />}
      {activeTab === 1 && <RmsCrudPanel />}
      {activeTab === 2 && <RabatyCrudPanel />}
      {activeTab === 3 && <EnginesCrudPanel />}
      {activeTab === 4 && <DepreciationRatesPanel />}
      {activeTab === 5 && <MileageCorrectionsPanel />}
      {activeTab === 6 && <ServiceCostsCrudPanel />}
      {activeTab === 7 && <TabelaOponCrudPanel />}
      {activeTab === 8 && <BrandCorrectionCrudPanel />}
      {activeTab === 9 && <ReplacementCarCrudPanel />}
    </Box>
  );
}


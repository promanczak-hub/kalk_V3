import { useState } from "react";
import { Box, Tabs, Tab } from "@mui/material";
import RmsCrudPanel from "./RmsCrud/RmsCrudPanel";
import RabatyCrudPanel from "./RabatyCrud/RabatyCrudPanel";
import EnginesCrudPanel from "./EnginesCrud/EnginesCrudPanel";
import TabelaOponCrudPanel from "./TabelaOponCrud/TabelaOponCrudPanel";
import GlobalSettingsPanel from "./GlobalSettingsPanel";
import SamarMasterPanel from "./SamarMasterPanel";

export default function ControlCenter() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 3 }}>
      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
        <Tabs value={activeTab} onChange={(_e, val) => setActiveTab(val)} variant="scrollable" scrollButtons="auto">
          <Tab label="Ustawienia Globalne" />
          <Tab label="📊 SAMAR Parametry" sx={{ fontWeight: 700 }} />
          <Tab label="Tabele RMS _czak" />
          <Tab label="Tabela rabaty" />
          <Tab label="Tabele Napędy" />
          <Tab label="Tabela Opon" />
        </Tabs>
      </Box>

      {activeTab === 0 && <GlobalSettingsPanel />}
      {activeTab === 1 && <SamarMasterPanel />}
      {activeTab === 2 && <RmsCrudPanel />}
      {activeTab === 3 && <RabatyCrudPanel />}
      {activeTab === 4 && <EnginesCrudPanel />}
      {activeTab === 5 && <TabelaOponCrudPanel />}
    </Box>
  );
}

import { useState } from "react";
import { Box, Tabs, Tab } from "@mui/material";
import RabatyCrudPanel from "./RabatyCrud/RabatyCrudPanel";
import EnginesCrudPanel from "./EnginesCrud/EnginesCrudPanel";
import TabelaOponCrudPanel from "./TabelaOponCrud/TabelaOponCrudPanel";
import GlobalSettingsPanel from "./GlobalSettingsPanel";
import SamarMasterPanel from "./SamarMasterPanel";
import ExcelDraftsPanel from "./ExcelDrafts/ExcelDraftsPanel";

export default function ControlCenter() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 3 }}>
      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
        <Tabs value={activeTab} onChange={(_e, val) => setActiveTab(val)} variant="scrollable" scrollButtons="auto">
          <Tab label="Ustawienia Globalne" />
          <Tab label="📊 SAMAR Parametry" sx={{ fontWeight: 700 }} />
          <Tab label="Tabela rabaty" />
          <Tab label="Tabele Napędy" />
          <Tab label="Tabela Opon" />
          <Tab label="📝 Modele Wyceny (Draft)" sx={{ fontWeight: 700, color: "secondary.main" }} />
        </Tabs>
      </Box>

      {activeTab === 0 && <GlobalSettingsPanel />}
      {activeTab === 1 && <SamarMasterPanel />}
      {activeTab === 2 && <RabatyCrudPanel />}
      {activeTab === 3 && <EnginesCrudPanel />}
      {activeTab === 4 && <TabelaOponCrudPanel />}
      {activeTab === 5 && <ExcelDraftsPanel />}
    </Box>
  );
}

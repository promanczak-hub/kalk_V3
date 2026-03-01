import { useState } from "react";
import { Box, Tabs, Tab } from "@mui/material";
import RmsCrudPanel from "./RmsCrud/RmsCrudPanel";
import RabatyCrudPanel from "./RabatyCrud/RabatyCrudPanel";
import EnginesCrudPanel from "./EnginesCrud/EnginesCrudPanel";
import ServiceCostsCrudPanel from "./ServiceCostsCrud/ServiceCostsCrudPanel";
import TabelaOponCrudPanel from "./TabelaOponCrud/TabelaOponCrudPanel";

export default function ControlCenter() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 3 }}>
      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
        <Tabs value={activeTab} onChange={(_e, val) => setActiveTab(val)}>
          <Tab label="Tabele RMS _czak" />
          <Tab label="Tabela rabaty" />
          <Tab label="Tabele Napędy" />
          <Tab label="Koszty Serwisowe" />
          <Tab label="Tabela Opon" />
        </Tabs>
      </Box>

      {activeTab === 0 && <RmsCrudPanel />}
      {activeTab === 1 && <RabatyCrudPanel />}
      {activeTab === 2 && <EnginesCrudPanel />}
      {activeTab === 3 && <ServiceCostsCrudPanel />}
      {activeTab === 4 && <TabelaOponCrudPanel />}
    </Box>
  );
}

import { useState } from "react";
import { Box, Tabs, Tab } from "@mui/material";
import RmsCrudPanel from "./RmsCrud/RmsCrudPanel";
import RabatyCrudPanel from "./RabatyCrud/RabatyCrudPanel";
import EnginesCrudPanel from "./EnginesCrud/EnginesCrudPanel";

export default function ControlCenter() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 3 }}>
      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
        <Tabs value={activeTab} onChange={(_e, val) => setActiveTab(val)}>
          <Tab label="Tabele RMS _czak" />
          <Tab label="Tabela rabaty" />
          <Tab label="Tabele Napędy" />
        </Tabs>
      </Box>

      {activeTab === 0 && <RmsCrudPanel />}
      {activeTab === 1 && <RabatyCrudPanel />}
      {activeTab === 2 && <EnginesCrudPanel />}
    </Box>
  );
}

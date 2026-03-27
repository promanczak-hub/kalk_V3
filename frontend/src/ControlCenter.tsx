import { useState } from "react";
import { Box, Tabs, Tab } from "@mui/material";
import GlobalSettingsPanel from "./GlobalSettingsPanel";
import ExcelDraftsPanel from "./ExcelDrafts/ExcelDraftsPanel";

export default function ControlCenter() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 3 }}>
      <Box sx={{ mb: 2 }}>
        <Tabs
          value={activeTab}
          onChange={(_e, val) => setActiveTab(val)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            minHeight: 40,
            "& .MuiTabs-indicator": { display: "none" },
            "& .MuiTab-root": {
              minHeight: 36,
              fontSize: "0.78rem",
              fontWeight: 500,
              textTransform: "none",
              borderRadius: "8px",
              mx: 0.3,
              px: 2,
              transition: "all 0.15s ease",
              "&:hover": { bgcolor: "action.hover" },
              "&.Mui-selected": {
                bgcolor: "primary.main",
                color: "primary.contrastText",
                fontWeight: 600,
              },
            },
          }}
        >
          <Tab label="Ustawienia Globalne" />
          <Tab label="📝 Modele Wyceny (Draft)" />
        </Tabs>
      </Box>

      {activeTab === 0 && <GlobalSettingsPanel />}
      {activeTab === 1 && <ExcelDraftsPanel />}
    </Box>
  );
}

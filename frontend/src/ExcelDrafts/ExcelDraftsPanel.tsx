import React, { useState, useEffect } from "react";
import { Box, Tabs, Tab, CircularProgress, Typography } from "@mui/material";
import DynamicGridEditor from "./DynamicGridEditor";

export default function ExcelDraftsPanel() {
  const [activeTab, setActiveTab] = useState(0);
  const [sheets, setSheets] = useState<{sheet_name: string}[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSheets = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/api/excel-drafts");
        if (res.ok) {
          const data = await res.json();
          setSheets(data);
        }
      } catch (err) {
        console.error("Error fetching sheets:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchSheets();
  }, []);

  if (loading) {
    return (
      <Box sx={{ p: 4, display: "flex", justifyContent: "center" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (sheets.length === 0) {
    return (
      <Box sx={{ p: 4 }}>
        <Typography>Brak arkuszy z Excela w bazie.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ width: "100%", typography: "body1" }}>
      <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          variant="scrollable"
          scrollButtons="auto"
        >
          {sheets.map((s, idx) => (
            <Tab key={idx} label={s.sheet_name} />
          ))}
        </Tabs>
      </Box>

      <Box sx={{ mt: 2 }}>
        <DynamicGridEditor sheetName={sheets[activeTab].sheet_name} />
      </Box>
    </Box>
  );
}

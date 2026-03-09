import { useState } from "react";
import { Box, Tab, Tabs, Typography } from "@mui/material";
import BaseRVCrudPanel from "./BaseRVCrud/BaseRVCrudPanel";
import DepreciationRatesPanel from "./DepreciationRatesCrud/DepreciationRatesPanel";
import MileageCorrectionsPanel from "./MileageCorrectionsCrud/MileageCorrectionsPanel";
import BrandCorrectionCrudPanel from "./BrandCorrectionCrud/BrandCorrectionCrudPanel";
import BodyCorrectionsCrudPanel from "./BodyCorrectionsCrud/BodyCorrectionsCrudPanel";
import PaintCorrectionCrudPanel from "./PaintCorrectionCrud/PaintCorrectionCrudPanel";
import VintageCorrectionCrudPanel from "./VintageCorrectionCrud/VintageCorrectionCrudPanel";

export default function ValuationModelsPanel() {
  const [subTab, setSubTab] = useState(0);

  const subTabs = [
    { label: "🛣️ Normatywy (Przebieg/Okres)", color: "#ff9800" },
    { label: "🔮 WR Klasa (Baza)", color: "#e91e63" },
    { label: "🏷️ Kor. Marka z Modelem", color: "#9c27b0" },
    { label: "📊 Doposażenie (Opcje)", color: "#f44336" },
    { label: "🚛 Kor. Nadwozia", color: "#795548" },
    { label: "🎨 Kor. Kolor (Lakier)", color: "#ab47bc" },
    { label: "📅 Kor. Rocznik", color: "#5c6bc0" },
  ];

  return (
    <Box>
      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
        <Tabs 
          value={subTab} 
          onChange={(_e, val) => setSubTab(val)} 
          variant="scrollable" 
          scrollButtons="auto" 
          sx={{ "& .MuiTab-root": { fontWeight: 600, fontSize: "0.8rem", textTransform: "none" } }}
        >
          {subTabs.map((t, i) => (
            <Tab key={i} label={t.label} sx={{ "&.Mui-selected": { color: t.color } }} />
          ))}
        </Tabs>
      </Box>

      {subTab === 0 && <MileageCorrectionsPanel />}
      {subTab === 1 && <BaseRVCrudPanel />}
      {subTab === 2 && <BrandCorrectionCrudPanel />}
      {subTab === 3 && <DepreciationRatesPanel />}
      {subTab === 4 && <BodyCorrectionsCrudPanel />}
      {subTab === 5 && <PaintCorrectionCrudPanel />}
      {subTab === 6 && <VintageCorrectionCrudPanel />}
    </Box>
  );
}

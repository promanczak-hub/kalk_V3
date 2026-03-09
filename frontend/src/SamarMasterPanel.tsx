import { useState, useEffect } from "react";
import {
  Box,
  Tab,
  Tabs,
  Typography,
  Paper,
  Chip,
  alpha,
  useTheme,

  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import DepreciationRatesPanel from "./DepreciationRatesCrud/DepreciationRatesPanel";
import MileageCorrectionsPanel from "./MileageCorrectionsCrud/MileageCorrectionsPanel";
import ServiceCostsCrudPanel from "./ServiceCostsCrud/ServiceCostsCrudPanel";
import ReplacementCarCrudPanel from "./ReplacementCarCrud/ReplacementCarCrudPanel";
import BrandCorrectionCrudPanel from "./BrandCorrectionCrud/BrandCorrectionCrudPanel";
import BodyCorrectionsCrudPanel from "./BodyCorrectionsCrud/BodyCorrectionsCrudPanel";
import ZabudowaCrudPanel from "./ZabudowaCrud/ZabudowaCrudPanel";
import InsuranceRatesCrudPanel from "./InsuranceRatesCrud/InsuranceRatesCrudPanel";
import DamageCoefficientsCrudPanel from "./DamageCoefficientsCrud/DamageCoefficientsCrudPanel";
import PaintCorrectionCrudPanel from "./PaintCorrectionCrud/PaintCorrectionCrudPanel";
import VintageCorrectionCrudPanel from "./VintageCorrectionCrud/VintageCorrectionCrudPanel";

import BaseRVCrudPanel from "./BaseRVCrud/BaseRVCrudPanel";

const BASE_URL = "http://127.0.0.1:8000";

interface SamarClass {
  id: number;
  name: string;
  base_mileage_km?: number;
  mileage_threshold_km?: number;
  base_period_months?: number;
  excel_code?: string;
  samar_class_id?: number;
  category?: string;
  size_class?: string;
  example_models?: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  Podstawowa: "#1976d2",
  "Sportowo-rekreacyjne": "#e91e63",
  "Terenowo-rekreacyjne (SUV)": "#4caf50",
  Vany: "#ff9800",
  Kombivany: "#9c27b0",
  Minibusy: "#00897b",
  "LEKKIE DOSTAWCZE": "#795548",
  "PICK-UP": "#bf360c",
  "ŚREDNIE DOSTAWCZE": "#5d4037",
  "CIĘŻKIE DOSTAWCZE": "#37474f",
  AUTOBUSY: "#006064",
};

/* ─────────── Master Table View ─────────── */
function MasterTableView({ classes }: { classes: SamarClass[] }) {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";

  // Group by category
  const grouped = classes.reduce(
    (acc, cls) => {
      const cat = cls.category || "INNE";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(cls);
      return acc;
    },
    {} as Record<string, SamarClass[]>
  );

  const categoryOrder = [
    "Podstawowa",
    "Sportowo-rekreacyjne",
    "Terenowo-rekreacyjne (SUV)",
    "Vany",
    "Kombivany",
    "Minibusy",
    "LEKKIE DOSTAWCZE",
    "PICK-UP",
    "ŚREDNIE DOSTAWCZE",
    "CIĘŻKIE DOSTAWCZE",
    "AUTOBUSY",
    "INNE",
  ];

  return (
    <Box>
      <Paper
        elevation={0}
        sx={{
          p: 2,
          mb: 2,
          borderRadius: 2,
          bgcolor: isDark ? alpha("#0d47a1", 0.08) : alpha("#e3f2fd", 0.5),
          border: `1px solid ${isDark ? "#1565c0" : "#90caf9"}`,
        }}
      >
        <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5, display: "flex", alignItems: "center", gap: 1 }}>
          🗂️ SAMAR Master Table — {classes.length} klas
          <Chip
            label="ZAMROŻONE"
            size="small"
            color="error"
            sx={{ fontWeight: "bold", height: 20, fontSize: "0.65rem" }}
          />
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          Unified view: samar_classes + samar_class_id bridge + Excel codes +
          example models. Źródło prawdy dla wszystkich modułów kalkulatora. Tabela ZAMROŻONA - brak edycji.
        </Typography>
      </Paper>

      {categoryOrder.map((cat) => {
        const items = grouped[cat];
        if (!items) return null;
        const catColor = CATEGORY_COLORS[cat] || "#757575";

        return (
          <Paper
            key={cat}
            elevation={0}
            sx={{
              mb: 2,
              borderRadius: 2,
              overflow: "hidden",
              border: `1px solid ${alpha(catColor, 0.3)}`,
            }}
          >
            <Box
              sx={{
                px: 2,
                py: 0.8,
                bgcolor: alpha(catColor, isDark ? 0.15 : 0.08),
                borderBottom: `2px solid ${catColor}`,
                display: "flex",
                alignItems: "center",
                gap: 1,
              }}
            >
              <Typography
                sx={{ fontWeight: 700, fontSize: "0.85rem", color: catColor }}
              >
                {cat}
              </Typography>
              <Chip
                label={`${items.length} klas`}
                size="small"
                sx={{
                  bgcolor: alpha(catColor, 0.15),
                  color: catColor,
                  fontWeight: 600,
                  fontSize: "0.65rem",
                  height: 20,
                }}
              />
            </Box>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow
                    sx={{
                      bgcolor: isDark
                        ? alpha(catColor, 0.05)
                        : alpha(catColor, 0.02),
                    }}
                  >
                    <TableCell sx={{ fontWeight: 700, width: 50 }}>ID</TableCell>
                    <TableCell sx={{ fontWeight: 700, width: 180 }}>
                      Segment
                    </TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Pełna nazwa</TableCell>
                    <TableCell sx={{ fontWeight: 700, minWidth: 300 }}>
                      Przykładowe modele
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {items.map((cls) => (
                    <TableRow
                      key={cls.id}
                      sx={{
                        "&:hover": {
                          bgcolor: alpha(catColor, isDark ? 0.08 : 0.03),
                        },
                      }}
                    >
                      <TableCell>
                        <Chip
                          label={cls.id}
                          size="small"
                          sx={{
                            fontFamily: "monospace",
                            fontWeight: 700,
                            fontSize: "0.7rem",
                            height: 22,
                            bgcolor: alpha(catColor, 0.1),
                            color: catColor,
                          }}
                        />
                      </TableCell>
                      <TableCell>{cls.size_class || "—"}</TableCell>
                      <TableCell
                        sx={{ fontSize: "0.8rem", fontWeight: 500 }}
                      >
                        {cls.name}
                      </TableCell>
                      <TableCell
                        sx={{
                          fontSize: "0.7rem",
                          color: "text.secondary",
                          maxWidth: 350,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                        title={cls.example_models || ""}
                      >
                        {cls.example_models || "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        );
      })}
    </Box>
  );
}



/* ─────────── Main Panel ─────────── */
export default function SamarMasterPanel() {
  const [classes, setClasses] = useState<SamarClass[]>([]);
  const [subTab, setSubTab] = useState(0);


  useEffect(() => {
    fetch(`${BASE_URL}/api/samar-classes`)
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setClasses(data);
        }
      })
      .catch(console.error);
  }, []);



  const subTabs = [
    { label: "🗂️ Master Table", color: "#1565c0" },
    { label: "🔮 Bazowe WR", color: "#e91e63" },
    { label: "📊 Deprecjacja", color: "#f44336" },
    { label: "🛣️ Przebieg", color: "#ff9800" },
    { label: "🔧 Serwis", color: "#4caf50" },
    { label: "🚗 Auto Zastępcze", color: "#2196f3" },
    { label: "🏷️ Korekta Marka", color: "#9c27b0" },
    { label: "🚛 Korekta Nadwozia", color: "#795548" },
    { label: "🏗️ Zabudowa", color: "#6d4c41" },
    { label: "🛡️ Ubezpieczenie", color: "#00897b" },
    { label: "💥 Wsp. Szkodowe", color: "#e65100" },
    { label: "🎨 Korekta Lakier", color: "#ab47bc" },
    { label: "📅 Korekta Rocznik", color: "#5c6bc0" },

  ];

  return (
    <Box>



      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
        <Tabs value={subTab} onChange={(_e, val) => setSubTab(val)} variant="scrollable" scrollButtons="auto" sx={{ "& .MuiTab-root": { fontWeight: 600, fontSize: "0.8rem", textTransform: "none" } }}>
          {subTabs.map((t, i) => (
            <Tab key={i} label={t.label} sx={{ "&.Mui-selected": { color: t.color } }} />
          ))}
        </Tabs>
      </Box>

      {subTab === 0 && <MasterTableView classes={classes} />}
      {subTab === 1 && <BaseRVCrudPanel />}
      {subTab === 2 && <DepreciationRatesPanel />}
      {subTab === 3 && <MileageCorrectionsPanel />}
      {subTab === 4 && <ServiceCostsCrudPanel />}
      {subTab === 5 && <ReplacementCarCrudPanel />}
      {subTab === 6 && <BrandCorrectionCrudPanel />}
      {subTab === 7 && <BodyCorrectionsCrudPanel />}
      {subTab === 8 && <ZabudowaCrudPanel />}
      {subTab === 9 && <InsuranceRatesCrudPanel />}
      {subTab === 10 && <DamageCoefficientsCrudPanel />}
      {subTab === 11 && <PaintCorrectionCrudPanel />}
      {subTab === 12 && <VintageCorrectionCrudPanel />}

    </Box>
  );
}

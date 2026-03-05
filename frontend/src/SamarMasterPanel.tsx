import { useState, useEffect } from "react";
import {
  Box,
  Tab,
  Tabs,
  Typography,
  Select,
  MenuItem,
  Paper,
  Chip,
  alpha,
  useTheme,
  Tooltip,
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
import InsuranceRatesCrudPanel from "./InsuranceRatesCrud/InsuranceRatesCrudPanel";
import DamageCoefficientsCrudPanel from "./DamageCoefficientsCrud/DamageCoefficientsCrudPanel";

const BASE_URL = "http://127.0.0.1:8000";

interface SamarClass {
  id: number;
  name: string;
  base_mileage_km?: number;
  mileage_threshold_km?: number;
  base_period_months?: number;
  excel_code?: string;
  klasa_wr_id?: number;
  category?: string;
  size_class?: string;
  example_models?: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  PODSTAWOWA: "#1976d2",
  "SPORTOWO-REKREACYJNE": "#e91e63",
  "TERENOWO-REKREACYJNE": "#4caf50",
  VANY: "#ff9800",
  KOMBIVANY: "#9c27b0",
  MINIBUS: "#00897b",
  "S. DOSTAWCZE DO 6T": "#795548",
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
    "PODSTAWOWA",
    "SPORTOWO-REKREACYJNE",
    "TERENOWO-REKREACYJNE",
    "VANY",
    "KOMBIVANY",
    "MINIBUS",
    "S. DOSTAWCZE DO 6T",
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
        <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
          🗂️ SAMAR Master Table — {classes.length} klas
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          Unified view: samar_classes + klasa_wr_id bridge + Excel codes +
          example models. Źródło prawdy dla wszystkich modułów kalkulatora.
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
                    <TableCell sx={{ fontWeight: 700, width: 40 }}>ID</TableCell>
                    <TableCell sx={{ fontWeight: 700, width: 70 }}>
                      Kod Excel
                    </TableCell>
                    <TableCell sx={{ fontWeight: 700, width: 50 }}>
                      WR ID
                    </TableCell>
                    <TableCell sx={{ fontWeight: 700, width: 180 }}>
                      Segment
                    </TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Pełna nazwa</TableCell>
                    <TableCell sx={{ fontWeight: 700, minWidth: 250 }}>
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
                      <TableCell
                        sx={{ fontFamily: "monospace", fontWeight: 600 }}
                      >
                        {cls.excel_code || "—"}
                      </TableCell>
                      <TableCell sx={{ fontFamily: "monospace" }}>
                        {cls.klasa_wr_id || "—"}
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
  const [selectedClassId, setSelectedClassId] = useState<number>(1);
  const [subTab, setSubTab] = useState(0);


  useEffect(() => {
    fetch(`${BASE_URL}/api/samar-classes`)
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setClasses(data);
          setSelectedClassId(data[0].id);
        }
      })
      .catch(console.error);
  }, []);



  const subTabs = [
    { label: "🗂️ Master Table", color: "#1565c0" },
    { label: "📊 Deprecjacja", color: "#f44336" },
    { label: "🛣️ Przebieg", color: "#ff9800" },
    { label: "🔧 Serwis", color: "#4caf50" },
    { label: "🚗 Auto Zastępcze", color: "#2196f3" },
    { label: "🏷️ Korekta Marka", color: "#9c27b0" },
    { label: "🚛 Korekta Nadwozia", color: "#795548" },
    { label: "🛡️ Ubezpieczenie", color: "#00897b" },
    { label: "💥 Wsp. Szkodowe", color: "#e65100" },
  ];

  return (
    <Box>

      <Paper elevation={0} sx={{ p: 1.5, mb: 2, borderRadius: 2, border: "1px solid", borderColor: "divider" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
          <Typography variant="body2" sx={{ fontWeight: 600, whiteSpace: "nowrap" }}>Klasa SAMAR:</Typography>
          <Select value={selectedClassId} onChange={(e) => setSelectedClassId(Number(e.target.value))} size="small" sx={{ minWidth: 350, fontWeight: 600, fontSize: "0.85rem" }}>
            {classes.map((c) => (
              <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>
            ))}
          </Select>
          <Chip label={`ID: ${selectedClassId}`} size="small" variant="outlined" sx={{ fontFamily: "monospace", fontSize: "0.75rem" }} />
        </Box>
        {(() => {
          const cls = classes.find((c) => c.id === selectedClassId);
          const baseMileage = cls?.base_mileage_km ?? 140000;
          const threshold = cls?.mileage_threshold_km ?? 190000;
          const basePeriod = cls?.base_period_months ?? 48;
          return (
            <Box sx={{ display: "flex", gap: 1, mt: 1, flexWrap: "wrap" }}>
              <Chip
                icon={<Typography sx={{ fontSize: "0.65rem", pl: 0.5 }}>📅</Typography>}
                label={`Okres bazowy: ${basePeriod} mies`}
                size="small"
                sx={{ fontSize: "0.7rem", bgcolor: "rgba(25,118,210,0.08)", fontWeight: 600 }}
              />
              <Chip
                icon={<Typography sx={{ fontSize: "0.65rem", pl: 0.5 }}>🛣️</Typography>}
                label={`Przebieg bazowy: ${(baseMileage / 1000).toFixed(0)}k km`}
                size="small"
                sx={{ fontSize: "0.7rem", bgcolor: "rgba(76,175,80,0.08)", fontWeight: 600 }}
              />
              <Chip
                icon={<Typography sx={{ fontSize: "0.65rem", pl: 0.5 }}>⚠️</Typography>}
                label={`Próg przebiegowy: ${(threshold / 1000).toFixed(0)}k km`}
                size="small"
                sx={{ fontSize: "0.7rem", bgcolor: "rgba(255,152,0,0.08)", fontWeight: 600 }}
              />
            </Box>
          );
        })()}
      </Paper>

      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
        <Tabs value={subTab} onChange={(_e, val) => setSubTab(val)} variant="fullWidth" sx={{ "& .MuiTab-root": { fontWeight: 600, fontSize: "0.8rem", textTransform: "none" } }}>
          {subTabs.map((t, i) => (
            <Tab key={i} label={t.label} sx={{ "&.Mui-selected": { color: t.color } }} />
          ))}
        </Tabs>
      </Box>

      {subTab === 0 && <MasterTableView classes={classes} />}
      {subTab === 1 && <DepreciationRatesPanel samarClassId={selectedClassId} />}
      {subTab === 2 && <MileageCorrectionsPanel samarClassId={selectedClassId} />}
      {subTab === 3 && <ServiceCostsCrudPanel />}
      {subTab === 4 && <ReplacementCarCrudPanel />}
      {subTab === 5 && <BrandCorrectionCrudPanel />}
      {subTab === 6 && <BodyCorrectionsCrudPanel samarClassId={selectedClassId} />}
      {subTab === 7 && <InsuranceRatesCrudPanel />}
      {subTab === 8 && <DamageCoefficientsCrudPanel />}
    </Box>
  );
}

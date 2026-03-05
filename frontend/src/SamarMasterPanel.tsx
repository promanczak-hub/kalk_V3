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
} from "@mui/material";
import DepreciationRatesPanel from "./DepreciationRatesCrud/DepreciationRatesPanel";
import MileageCorrectionsPanel from "./MileageCorrectionsCrud/MileageCorrectionsPanel";
import ServiceCostsCrudPanel from "./ServiceCostsCrud/ServiceCostsCrudPanel";
import ReplacementCarCrudPanel from "./ReplacementCarCrud/ReplacementCarCrudPanel";
import BrandCorrectionCrudPanel from "./BrandCorrectionCrud/BrandCorrectionCrudPanel";
import BodyTypesCrudPanel from "./BodyTypesCrud/BodyTypesCrudPanel";
import InsuranceRatesCrudPanel from "./InsuranceRatesCrud/InsuranceRatesCrudPanel";
import DamageCoefficientsCrudPanel from "./DamageCoefficientsCrud/DamageCoefficientsCrudPanel";

const BASE_URL = "http://127.0.0.1:8000";

interface SamarClass {
  id: number;
  name: string;
  base_mileage_km?: number;
  mileage_threshold_km?: number;
  base_period_months?: number;
}

/* ─────────── Pipeline step box ─────────── */
function StepBox({
  color,
  icon,
  label,
  tableName,
  count,
  keysDesc,
  step,
  tooltip,
}: {
  color: string;
  icon: string;
  label: string;
  tableName: string;
  count: number | string;
  keysDesc: string;
  step: string;
  tooltip?: string;
}) {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";
  const content = (
    <Box
      sx={{
        flex: 1,
        minWidth: 120,
        p: 0.8,
        borderRadius: 1.5,
        border: `2px solid ${color}`,
        bgcolor: alpha(color, isDark ? 0.12 : 0.05),
        textAlign: "center",
        transition: "all 0.2s ease",
        position: "relative",
        "&:hover": {
          bgcolor: alpha(color, isDark ? 0.22 : 0.1),
          transform: "translateY(-2px)",
          boxShadow: `0 4px 12px ${alpha(color, 0.25)}`,
        },
      }}
    >
      <Chip
        label={step}
        size="small"
        sx={{
          position: "absolute",
          top: -10,
          right: -6,
          fontSize: "0.5rem",
          height: 18,
          minWidth: 18,
          bgcolor: color,
          color: "#fff",
          fontWeight: 800,
          "& .MuiChip-label": { px: 0.5 },
        }}
      />
      <Typography sx={{ color, fontWeight: 700, fontSize: "0.55rem" }}>
        {icon} {label}
      </Typography>
      <Typography sx={{ fontWeight: 500, fontSize: "0.45rem", color: "text.primary", opacity: 0.6 }}>
        {tableName}
      </Typography>
      <Chip label={`${count}`} size="small" sx={{ mt: 0.2, fontSize: "0.5rem", height: 16 }} />
      <Typography sx={{ color: "text.secondary", fontSize: "0.42rem", mt: 0.2 }}>
        {keysDesc}
      </Typography>
    </Box>
  );
  return tooltip ? <Tooltip title={tooltip} arrow placement="top"><Box sx={{ flex: 1, minWidth: 120 }}>{content}</Box></Tooltip> : content;
}

/* ─────────── Architecture Diagram ─────────── */
function ArchitectureDiagram({
  classes,
  selectedId,
  stats,
}: {
  classes: SamarClass[];
  selectedId: number;
  stats: Record<string, number>;
}) {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";
  const selectedClass = classes.find((c) => c.id === selectedId);

  const hubBg = isDark
    ? "linear-gradient(135deg, #1a237e 0%, #283593 100%)"
    : "linear-gradient(135deg, #1565c0 0%, #1976d2 100%)";

  const groupSx = (color: string) => ({
    p: 1.2,
    borderRadius: 2,
    border: `2px solid ${color}`,
    bgcolor: alpha(color, isDark ? 0.05 : 0.02),
    position: "relative" as const,
    "&::before": {
      content: '""',
      position: "absolute",
      top: -14,
      left: "50%",
      transform: "translateX(-50%)",
      width: 2,
      height: 14,
      bgcolor: isDark ? "#555" : "#bbb",
    },
  });

  return (
    <Paper elevation={0} sx={{ p: 2, mb: 2, borderRadius: 3, bgcolor: isDark ? alpha("#0d1117", 0.8) : alpha("#f5f5f5", 0.6), border: `1px solid ${isDark ? "#30363d" : "#e0e0e0"}` }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
        <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 600, letterSpacing: 1, textTransform: "uppercase", fontSize: "0.6rem" }}>
          Pipeline SAMAR WR — kolejność kroków z V1
        </Typography>
      </Box>

      {/* Hub */}
      <Box sx={{ background: hubBg, color: "#fff", p: 1.2, borderRadius: 2, textAlign: "center", boxShadow: "0 4px 20px rgba(25,118,210,0.3)" }}>
        <Typography variant="overline" sx={{ opacity: 0.8, letterSpacing: 2, fontSize: "0.5rem" }}>MASTER HUB</Typography>
        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>samar_classes</Typography>
        <Chip label={selectedClass?.name || "—"} size="small" sx={{ bgcolor: "rgba(255,255,255,0.2)", color: "#fff", fontWeight: 600, fontSize: "0.6rem" }} />
        <Typography variant="caption" sx={{ display: "block", mt: 0.2, opacity: 0.7, fontSize: "0.5rem" }}>
          {classes.length} klas · ID: {selectedId}
        </Typography>
      </Box>

      {/* Connector */}
      <Box sx={{ display: "flex", justifyContent: "center" }}>
        <Box sx={{ width: 2, height: 12, bgcolor: isDark ? "#555" : "#bbb" }} />
      </Box>
      <Box sx={{ display: "flex", justifyContent: "center", mb: 1 }}>
        <Box sx={{ width: "92%", height: 2, bgcolor: isDark ? "#555" : "#bbb", position: "relative" }}>
          {[0, 33, 66, 100].map((pct) => (
            <Box key={pct} sx={{ position: "absolute", left: `${pct}%`, top: 0, width: 2, height: 12, bgcolor: isDark ? "#555" : "#bbb" }} />
          ))}
        </Box>
      </Box>

      <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap" }}>

        {/* ── KROK 6: UtW — rozbity na kolejność ── */}
        <Box sx={{ ...groupSx("#f44336"), flex: 4, minWidth: 500 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
            <Typography sx={{ color: "#f44336", fontWeight: 700, fontSize: "0.7rem" }}>
              📉 KROK 6: UTRATA WARTOŚCI (UtW)
            </Typography>
            <Chip label="V1: LTRSubCalculatorUtrataWartosciNew" size="small" sx={{ fontSize: "0.4rem", height: 16, bgcolor: alpha("#f44336", 0.1) }} />
          </Box>

          {/* Formula row */}
          <Box sx={{ bgcolor: isDark ? alpha("#f44336", 0.08) : alpha("#f44336", 0.04), p: 0.8, borderRadius: 1, mb: 1, border: `1px dashed ${alpha("#f44336", 0.3)}` }}>
            <Typography sx={{ fontSize: "0.5rem", color: "text.secondary", fontFamily: "monospace", lineHeight: 1.6 }}>
              6.1 wrProcent48 = <b>bazowy%</b> + <b>marka%</b><br />
              6.2 wrWartosc48 = wrProcent48 × cenaCatalogowa<br />
              6.3 WRpoLatach = wrWartosc48 × <b>korekty_okresu[]</b><br />
              6.4 + doposażenie × <b>retencja_opcji%</b><br />
              6.5 + cenaCat × <b>kolor%</b><br />
              6.6 + cenaCałk × <b>zabudowa%</b><br />
              6.7 − <b>korekta_przebiegu</b> (kwotowo)<br />
              6.8 + korektaWR (ręczna)<br />
              6.9 WRbrutto = WR × (1 + <b>rocznik%</b>)
            </Typography>
          </Box>

          <Box sx={{ display: "flex", gap: 0.6, flexWrap: "wrap" }}>
            <StepBox step="6.1" color="#f44336" icon="📊" label="BAZOWY WR%" tableName="depreciation_rates" count={stats.depr} keysDesc="TAB.WR KLASA" tooltip="wrKlasaProcent: bazowy % WR dla 48 mies/140k km (np. 46% dla klasy B benzyna)" />
            <StepBox step="6.1" color="#9c27b0" icon="🏷️" label="+ MARKA %" tableName="korekta_wr_markas" count={stats.brand} keysDesc="brand_name" tooltip="wrMarkaProcent: dodawane do bazowego (np. chińskie −20%). Szuka w tabeli po brand_name." />
            <StepBox step="6.3" color="#ff5722" icon="📅" label="× OKRES" tableName="depreciation_rates" count={"y1-7"} keysDesc="TAB. OKRES FINAL" tooltip="Korekta za skrócony/wydłużony okres vs baza 48 mies. Jeśli lat<4: WR×(1+depr%), jeśli lat>4: WR×(1−depr%)" />
            <StepBox step="6.4" color="#e91e63" icon="🎯" label="+ OPCJE" tableName="depreciation_rates" count={"ret%"} keysDesc="TAB. DOPOSAŻENIA" tooltip="Opcje fabryczne × retencja%. Np. rok 0: 44% zachowane, rok 4: 24%, rok 7: 12%" />
            <StepBox step="6.5" color="#e91e63" icon="🎨" label="+ KOLOR" tableName="paint_adjustments" count={stats.paint} keysDesc="metalik/nie" tooltip="metalik=0%, niemetalik=−1% ceny kat." />
            <StepBox step="6.6" color="#795548" icon="🚛" label="+ ZABUDOWA" tableName="(w kodzie)" count={3} keysDesc="ND/P/Px" tooltip="ND=0%, P=0%, Px=+4% łącznej ceny zakupu" />
            <StepBox step="6.7" color="#ff9800" icon="🛣️" label="− PRZEBIEG" tableName="mileage_corrections" count={stats.mileage} keysDesc="kwotowo" tooltip="Korekta za przebieg: (km−140k)/10k × stawka% × WR. Próg 190k z inną stawką." />
            <StepBox step="6.9" color="#607d8b" icon="📅" label="× ROCZNIK" tableName="(w kodzie)" count={2} keysDesc="ostatnia!" tooltip="OSTATNIA korekta: mnożnik (1 + rocznik%). Np. −1 rok = ×0.92 (−8%)" />
          </Box>
        </Box>

        {/* ── KROK 4: SERWIS ── */}
        <Box sx={{ ...groupSx("#4caf50"), flex: 1, minWidth: 140 }}>
          <Typography sx={{ color: "#4caf50", fontWeight: 700, fontSize: "0.65rem", mb: 0.5 }}>
            🔧 KROK 4
          </Typography>
          <Box sx={{ bgcolor: isDark ? alpha("#4caf50", 0.08) : alpha("#4caf50", 0.04), p: 0.6, borderRadius: 1, mb: 0.8, border: `1px dashed ${alpha("#4caf50", 0.3)}` }}>
            <Typography sx={{ fontSize: "0.45rem", color: "text.secondary" }}>
              Opcje serwisowe<br /><b>odjęte od CAPEX</b><br />nie wchodzą do WR
            </Typography>
          </Box>
          <StepBox step="4" color="#4caf50" icon="⚙️" label="SERWIS" tableName="service_costs" count={stats.service} keysDesc="klasa×silnik×band" tooltip="Stawka serwisowa per km × przebieg. Opcje serwisowe tracą 100% — odjęte od ceny zakupu." />
        </Box>

        {/* ── KROK 3: AUTO ZASTĘPCZE ── */}
        <Box sx={{ ...groupSx("#2196f3"), flex: 1, minWidth: 140 }}>
          <Typography sx={{ color: "#2196f3", fontWeight: 700, fontSize: "0.65rem", mb: 0.5 }}>
            🚗 KROK 3
          </Typography>
          <StepBox step="3" color="#2196f3" icon="🔑" label="AUTO ZAST." tableName="replacement_car_rates" count={stats.replacement} keysDesc="klasa·dzień" tooltip="Stawka dzienna netto za auto zastępcze per klasa SAMAR" />
        </Box>

        {/* ── KROK 8: UBEZPIECZENIE ── */}
        <Box sx={{ ...groupSx("#00897b"), flex: 2, minWidth: 280 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
            <Typography sx={{ color: "#00897b", fontWeight: 700, fontSize: "0.7rem" }}>
              🛡️ KROK 8: UBEZPIECZENIE
            </Typography>
            <Chip label="V1: LTRSubCalculatorUbezpieczenie" size="small" sx={{ fontSize: "0.4rem", height: 16, bgcolor: alpha("#00897b", 0.1) }} />
          </Box>
          <Box sx={{ bgcolor: isDark ? alpha("#00897b", 0.08) : alpha("#00897b", 0.04), p: 0.6, borderRadius: 1, mb: 0.8, border: `1px dashed ${alpha("#00897b", 0.3)}` }}>
            <Typography sx={{ fontSize: "0.45rem", color: "text.secondary", fontFamily: "monospace", lineHeight: 1.6 }}>
              8.1 podstawa = CAPEX × (1 − (r−1)×12 × amort%)<br />
              8.2 AC = stawkaBazowaAC × podstawa<br />
              8.3 OC = stała roczna z tabeli<br />
              8.4 + średniaWartośćSzkody × wsp_przebieg × wsp_szkody
            </Typography>
          </Box>
          <Box sx={{ display: "flex", gap: 0.6, flexWrap: "wrap" }}>
            <StepBox step="8.1" color="#00897b" icon="🛡️" label="AC / OC" tableName="ltr_admin_ubezpieczenia" count={stats.insurance} keysDesc="rok×klasa" tooltip="Stawki AC% i OC (PLN/rok) per kolejny rok per klasa SAMAR" />
            <StepBox step="8.4" color="#e65100" icon="💥" label="WSP. SZKÓD" tableName="ltr_admin_wspolczynniki_szkodowe" count={stats.damage} keysDesc="klasa" tooltip="Współczynniki szkodowe: wsp_sredni_przebieg × wsp_wartosc_szkody" />
          </Box>
        </Box>
      </Box>
    </Paper>
  );
}

/* ─────────── Main Panel ─────────── */
export default function SamarMasterPanel() {
  const [classes, setClasses] = useState<SamarClass[]>([]);
  const [selectedClassId, setSelectedClassId] = useState<number>(1);
  const [subTab, setSubTab] = useState(0);
  const [stats, setStats] = useState<Record<string, number>>({
    depr: 0, mileage: 0, service: 0, replacement: 0, brand: 0, paint: 0, insurance: 0, damage: 0,
  });

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

  useEffect(() => {
    const endpoints: [string, string][] = [
      ["depr", "/api/depreciation-rates"],
      ["mileage", "/api/mileage-corrections"],
      ["service", "/api/samar-service-costs"],
      ["replacement", "/api/replacement-car-rates"],
      ["brand", "/api/brand-corrections"],
      ["paint", "/api/paint-adjustments"],
      ["insurance", "/api/samar-rv/insurance-rates"],
      ["damage", "/api/samar-rv/insurance-coefficients"],
    ];
    Promise.allSettled(
      endpoints.map(([, url]) => fetch(`${BASE_URL}${url}`).then((r) => r.json()))
    ).then((results) => {
      const s: Record<string, number> = {};
      results.forEach((r, i) => {
        const key = endpoints[i][0];
        s[key] = r.status === "fulfilled" && Array.isArray(r.value) ? r.value.length : 0;
      });
      setStats(s);
    });
  }, []);

  const subTabs = [
    { label: "📊 Deprecjacja", color: "#f44336" },
    { label: "🛣️ Przebieg", color: "#ff9800" },
    { label: "🔧 Serwis", color: "#4caf50" },
    { label: "🚗 Auto Zastępcze", color: "#2196f3" },
    { label: "🏷️ Korekta Marka", color: "#9c27b0" },
    { label: "🚛 Typy Nadwozia", color: "#795548" },
    { label: "🛡️ Ubezpieczenie", color: "#00897b" },
    { label: "💥 Wsp. Szkodowe", color: "#e65100" },
  ];

  return (
    <Box>
      <ArchitectureDiagram classes={classes} selectedId={selectedClassId} stats={stats} />

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

      {subTab === 0 && <DepreciationRatesPanel />}
      {subTab === 1 && <MileageCorrectionsPanel />}
      {subTab === 2 && <ServiceCostsCrudPanel />}
      {subTab === 3 && <ReplacementCarCrudPanel />}
      {subTab === 4 && <BrandCorrectionCrudPanel />}
      {subTab === 5 && <BodyTypesCrudPanel />}
      {subTab === 6 && <InsuranceRatesCrudPanel />}
      {subTab === 7 && <DamageCoefficientsCrudPanel />}
    </Box>
  );
}

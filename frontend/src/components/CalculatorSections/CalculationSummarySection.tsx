import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Grid,
  TextField,
  InputAdornment,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { Calculator } from "lucide-react";
import type { CalculatorInput } from "../../types";

interface CalculationSummarySectionProps {
  data: CalculatorInput;
  expanded: string | false;
  handleChange: (panel: string) => (event: React.SyntheticEvent, isExpanded: boolean) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  handleUpdate: (field: keyof CalculatorInput, value: any) => void;
}

export default function CalculationSummarySection({
  data,
  expanded,
  handleChange,
  handleUpdate,
}: CalculationSummarySectionProps) {
  return (
    <Accordion
      expanded={expanded === "panel3"}
      onChange={handleChange("panel3")}
      sx={{
        borderRadius: "8px !important",
        overflow: "hidden",
        boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
        "&:before": { display: "none" },
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        sx={{
          bgcolor: "rgba(30, 58, 138, 0.03)",
          borderBottom: "1px solid rgba(0,0,0,0.06)",
        }}
      >
        <Typography
          variant="h6"
          sx={{ display: "flex", alignItems: "center", gap: 1 }}
        >
          <Calculator size={20} color="#1e3a8a" />
          Podsumowanie Kalkulacji
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ p: 3 }}>
        <Grid container spacing={4}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Typography variant="subtitle2" color="primary" sx={{ mb: 2 }}>
              Parametry operacyjne (Wymagane do przeliczeń)
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 6 }}>
                <TextField
                  fullWidth
                  disabled
                  label="Okres używania (Mce)"
                  value={data.duration_months}
                  size="small"
                />
              </Grid>
              <Grid size={{ xs: 6 }}>
                <TextField
                  fullWidth
                  disabled
                  label="Dekl. przebieg całkowity (km)"
                  value={data.annual_mileage}
                  size="small"
                />
              </Grid>
              <Grid size={{ xs: 6 }}>
                <TextField
                  fullWidth
                  disabled
                  label="Czynsz inicjalny"
                  type="number"
                  value={data.initial_rent}
                  size="small"
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">%</InputAdornment>
                    ),
                  }}
                />
              </Grid>
            </Grid>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <Typography variant="subtitle2" color="primary" sx={{ mb: 2 }}>
              Zmienne globalne i finansowe
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 6 }}>
                <TextField
                  fullWidth
                  label="Bieżący WIBOR"
                  type="number"
                  inputProps={{ step: 0.01 }}
                  value={(data.wibor_pct * 100).toFixed(2)}
                  onChange={(e) => handleUpdate("wibor_pct", (parseFloat(e.target.value) || 0) / 100)}
                  size="small"
                  InputProps={{
                    endAdornment: <InputAdornment position="end">%</InputAdornment>,
                  }}
                  sx={{ bgcolor: "#fafafa" }}
                />
              </Grid>
              <Grid size={{ xs: 6 }}>
                <TextField
                  fullWidth
                  label="Marża Finansowa"
                  type="number"
                  inputProps={{ step: 0.01 }}
                  value={(data.financial_margin_pct * 100).toFixed(2)}
                  onChange={(e) => handleUpdate("financial_margin_pct", (parseFloat(e.target.value) || 0) / 100)}
                  size="small"
                  InputProps={{
                    endAdornment: <InputAdornment position="end">%</InputAdornment>,
                  }}
                  sx={{ bgcolor: "#fafafa" }}
                />
              </Grid>
              <Grid size={{ xs: 6 }}>
                <TextField
                  fullWidth
                  disabled
                  label="Procent Amortyzacji (Auto)"
                  value={data.amortization_pct ? (data.amortization_pct * 100).toFixed(2) : "—"}
                  size="small"
                  InputProps={{
                    endAdornment: <InputAdornment position="end">%</InputAdornment>,
                  }}
                  helperText="Obliczany dynamicznie z WP, WR i okresu"
                />
              </Grid>
            </Grid>
          </Grid>
        </Grid>
      </AccordionDetails>
    </Accordion>
  );
}


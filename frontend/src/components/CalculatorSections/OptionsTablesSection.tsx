import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  InputAdornment,
  Box,
  Switch,
  FormControlLabel,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { Settings, Truck, Shield, Percent } from "lucide-react";
import type { CalculatorInput } from "../../types";

interface OptionsTablesSectionProps {
  data: CalculatorInput;
  handleUpdate: (field: keyof CalculatorInput, value: any) => void;
  expanded?: boolean;
  onToggle?: (expanded: boolean) => void;
}

export default function OptionsTablesSection({
  data,
  handleUpdate,
  expanded = false,
  onToggle,
}: OptionsTablesSectionProps) {
  return (
    <Accordion
      expanded={expanded}
      onChange={(_, isExpanded) => onToggle?.(isExpanded)}
      sx={{
        borderRadius: "12px !important",
        overflow: "hidden",
        boxShadow: "0 10px 30px -10px rgba(0,0,0,0.1)",
        border: "1px solid rgba(0,0,0,0.05)",
        mb: 2,
        "&:before": { display: "none" },
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        sx={{
          bgcolor: "rgba(15, 23, 42, 0.02)",
          borderBottom: "1px solid rgba(0,0,0,0.06)",
          transition: "background-color 0.2s",
          "&:hover": { bgcolor: "rgba(15, 23, 42, 0.04)" }
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <Box 
            sx={{ 
              p: 1, 
              borderRadius: "8px", 
              bgcolor: "warning.main", 
              color: "white",
              display: "flex",
              alignItems: "center",
              justifyContent: "center"
            }}
          >
            <Settings size={18} />
          </Box>
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, color: "text.primary" }}>
              Ustawienia i Parametry
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Opony, Serwis, Auto Zastępcze i Finanse
            </Typography>
          </Box>
        </Box>
      </AccordionSummary>
      <AccordionDetails sx={{ p: 4 }}>
        <Grid container spacing={4}>
          {/* OPONY */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
              <Truck size={18} color="#f59e0b" />
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Opony i Logistyka</Typography>
            </Box>

            <Grid container spacing={2}>
              <Grid size={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={data.has_tires}
                      onChange={(e) => handleUpdate("has_tires", e.target.checked)}
                      color="warning"
                    />
                  }
                  label="Obsługa Opon (Serwis i Wymiana)"
                />
              </Grid>

              <Grid size={6}>
                <TextField
                  fullWidth
                  label="Rozmiar (Felga)"
                  value={data.tire_size.diameter}
                  onChange={(e) => handleUpdate("tire_size", { ...data.tire_size, diameter: e.target.value })}
                  size="small"
                  InputProps={{
                    startAdornment: <InputAdornment position="start">R</InputAdornment>,
                  }}
                />
              </Grid>
              <Grid size={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Klasa Opony</InputLabel>
                  <Select
                    value={data.tire_class}
                    label="Klasa Opony"
                    onChange={(e) => handleUpdate("tire_class", e.target.value)}
                  >
                    <MenuItem value="BUDGET">Budget</MenuItem>
                    <MenuItem value="MEDIUM">Medium</MenuItem>
                    <MenuItem value="PREMIUM">Premium</MenuItem>
                    <MenuItem value="WZMOCNIONE">Wzmocnione</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </Grid>

          {/* SERWIS I ZASTEPCZE */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
              <Shield size={18} color="#3b82f6" />
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Serwis i Ubezpieczenie</Typography>
            </Box>

            <Grid container spacing={2}>
              <Grid size={12}>
                 <FormControlLabel
                  control={
                    <Switch
                      checked={data.has_replacement_car}
                      onChange={(e) => handleUpdate("has_replacement_car", e.target.checked)}
                      color="primary"
                    />
                  }
                  label="Auto Zastępcze (Limitowane / Non-Stop)"
                />
              </Grid>
              <Grid size={6}>
                <TextField
                  fullWidth
                  label="Pakiet Serwisowy"
                  type="number"
                  value={data.service_package_amount}
                  onChange={(e) => handleUpdate("service_package_amount", parseFloat(e.target.value) || 0)}
                  size="small"
                  InputProps={{
                    endAdornment: <InputAdornment position="end">PLN</InputAdornment>,
                  }}
                />
              </Grid>
              <Grid size={6}>
                <TextField
                  fullWidth
                  label="Korekta WR (netto)"
                  type="number"
                  value={data.rv_correction}
                  onChange={(e) => handleUpdate("rv_correction", parseFloat(e.target.value) || 0)}
                  size="small"
                  sx={{ bgcolor: "rgba(34, 197, 94, 0.05)" }}
                />
              </Grid>
            </Grid>
          </Grid>

          {/* FINANSE */}
          <Grid size={12} sx={{ mt: 2 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
              <Percent size={18} color="#ef4444" />
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Parametry Finansowe</Typography>
            </Box>

            <Grid container spacing={3}>
              <Grid size={{ xs: 12, sm: 3 }}>
                <TextField
                  fullWidth
                  label="Oplata Wstępna %"
                  type="number"
                  value={data.initial_rent * 100}
                  onChange={(e) => handleUpdate("initial_rent", (parseFloat(e.target.value) || 0) / 100)}
                  size="small"
                  InputProps={{
                    endAdornment: <InputAdornment position="end">%</InputAdornment>,
                  }}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 3 }}>
                <TextField
                  fullWidth
                  label="WIBOR %"
                  type="number"
                  value={data.wibor_pct * 100}
                  onChange={(e) => handleUpdate("wibor_pct", (parseFloat(e.target.value) || 0) / 100)}
                  size="small"
                  InputProps={{
                    endAdornment: <InputAdornment position="end">%</InputAdornment>,
                  }}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 3 }}>
                <TextField
                  fullWidth
                  label="Marża Banku %"
                  type="number"
                  value={data.financial_margin_pct * 100}
                  onChange={(e) => handleUpdate("financial_margin_pct", (parseFloat(e.target.value) || 0) / 100)}
                  size="small"
                  InputProps={{
                    endAdornment: <InputAdornment position="end">%</InputAdornment>,
                  }}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 3 }}>
                <TextField
                  fullWidth
                  label="Marża Sprzedaży %"
                  type="number"
                  value={data.margin * 100}
                  onChange={(e) => handleUpdate("margin", (parseFloat(e.target.value) || 0) / 100)}
                  size="small"
                  sx={{
                    bgcolor: "rgba(239, 68, 68, 0.05)",
                    "& .MuiOutlinedInput-root": {
                      "& fieldset": { borderColor: "rgba(239, 68, 68, 0.2)" },
                    }
                  }}
                  InputProps={{
                    endAdornment: <InputAdornment position="end">%</InputAdornment>,
                  }}
                />
              </Grid>
            </Grid>
          </Grid>
        </Grid>
      </AccordionDetails>
    </Accordion>
  );
}

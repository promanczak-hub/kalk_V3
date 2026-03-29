import { useState, useEffect } from "react";
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
  ListSubheader,
  Box,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import axios from "axios";
import type { CalculatorInput } from "../../types";
import { Car, Calendar, Tag, Activity } from "lucide-react";
import { API_BASE_URL } from "../../config/env";

interface EngineOption {
  id: number;
  name: string;
  category: string;
  fuel_group_id: number;
}

interface BodyTypeOption {
  id: number;
  name: string;
  vehicle_class: string;
}

interface VehicleDataSectionProps {
  data: CalculatorInput;
  expanded?: boolean;
  onToggle?: (expanded: boolean) => void;
  handleUpdate: (field: keyof CalculatorInput, value: any) => void;
  handleUpdateNetto: (netto: number) => void;
  handleUpdateBrutto: (brutto: number) => void;
  handleChangeTypRabatu: (typ: "Procentowo" | "Kwotowo") => void;
  handleUpdateRabat: (typ: string, value: number) => void;
}

export default function VehicleDataSection({
  data,
  expanded = true,
  onToggle,
  handleUpdate,
  handleUpdateNetto,
  handleUpdateBrutto,
  handleChangeTypRabatu,
  handleUpdateRabat,
}: VehicleDataSectionProps) {
  const [engines, setEngines] = useState<EngineOption[]>([]);
  const [bodyTypes, setBodyTypes] = useState<BodyTypeOption[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [engRes, bodyRes] = await Promise.all([
          axios.get<EngineOption[]>(`${API_BASE_URL}/api/engines`),
          axios.get<BodyTypeOption[]>(`${API_BASE_URL}/api/body-types`),
        ]);
        setEngines(engRes.data);
        setBodyTypes(bodyRes.data);
      } catch (err) {
        console.error("Failed to load vehicle metadata:", err);
      }
    };
    fetchData();
  }, []);

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
              bgcolor: "primary.main", 
              color: "white",
              display: "flex",
              alignItems: "center",
              justifyContent: "center"
            }}
          >
            <Car size={18} />
          </Box>
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, color: "text.primary" }}>
              Dane Pojazdu
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Marka, Model, Silnik i Cena Bazowa
            </Typography>
          </Box>
        </Box>
      </AccordionSummary>
      <AccordionDetails sx={{ p: 4 }}>
        <Grid container spacing={4}>
          {/* IDENTYFIKACJA */}
          <Grid item xs={12}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
              <Tag size={16} color="#64748b" />
              <Typography variant="overline" sx={{ fontWeight: 700, letterSpacing: 1, color: "text.secondary" }}>
                Identyfikacja i Typowe Dane
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Marka"
              value={data.brand}
              onChange={(e) => handleUpdate("brand", e.target.value)}
              variant="outlined"
              placeholder="np. Toyota"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Model"
              value={typeof data.model === "object" ? data.model.dn : data.model}
              onChange={(e) =>
                handleUpdate("model", typeof data.model === "object" ? { ...data.model, dn: e.target.value } : e.target.value)
              }
              variant="outlined"
              placeholder="np. Corolla"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth>
              <InputLabel>Nadwozie</InputLabel>
              <Select
                value={data.body_type}
                label="Nadwozie"
                onChange={(e) => handleUpdate("body_type", e.target.value)}
              >
                {bodyTypes.map((bt) => (
                  <MenuItem key={bt.id} value={bt.name}>
                    {bt.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Wersja"
              value={data.trim_level}
              onChange={(e) => handleUpdate("trim_level", e.target.value)}
              variant="outlined"
              placeholder="np. Executive"
            />
          </Grid>

          {/* TECHNICZNE */}
          <Grid item xs={12} sx={{ mt: 1 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
              <Activity size={16} color="#64748b" />
              <Typography variant="overline" sx={{ fontWeight: 700, letterSpacing: 1, color: "text.secondary" }}>
                Parametry Techniczne
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Moc (KM)"
              type="number"
              value={data.engine_power_hp}
              onChange={(e) => handleUpdate("engine_power_hp", e.target.value)}
              InputProps={{
                endAdornment: <InputAdornment position="end">KM</InputAdornment>,
              }}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth>
              <InputLabel>Rodzaj Napędu / Paliwo</InputLabel>
              <Select
                value={data.fuel_type}
                label="Rodzaj Napędu / Paliwo"
                onChange={(e) => handleUpdate("fuel_type", e.target.value)}
              >
                {engines.length > 0 ? (
                  Object.entries(
                    engines.reduce<Record<string, EngineOption[]>>((acc, eng) => {
                      (acc[eng.category] = acc[eng.category] || []).push(eng);
                      return acc;
                    }, {})
                  ).flatMap(([category, items]) => [
                    <ListSubheader key={category}>{category}</ListSubheader>,
                    ...items.map((eng) => (
                      <MenuItem key={eng.id} value={eng.name}>
                        {eng.name}
                      </MenuItem>
                    )),
                  ])
                ) : (
                  <MenuItem disabled>Ładowanie...</MenuItem>
                )}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth>
              <InputLabel>Homologacja</InputLabel>
              <Select
                value={data.homologation_type}
                label="Homologacja"
                onChange={(e) => handleUpdate("homologation_type", e.target.value)}
              >
                <MenuItem value="Osobowy">Osobowy</MenuItem>
                <MenuItem value="Ciężarowy">Ciężarowy (N1)</MenuItem>
                <MenuItem value="Dostawczy">Dostawczy</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Rocznik"
              value={data.production_year}
              onChange={(e) => handleUpdate("production_year", e.target.value)}
              variant="outlined"
            />
          </Grid>

          {/* CENA */}
          <Grid item xs={12} sx={{ mt: 1 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
              <Calendar size={16} color="#64748b" />
              <Typography variant="overline" sx={{ fontWeight: 700, letterSpacing: 1, color: "text.secondary" }}>
                Wycena i Rabat
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Cena Cennikowa Netto"
              type="number"
              value={data.base_price_net}
              onChange={(e) => handleUpdateNetto(parseFloat(e.target.value) || 0)}
              InputProps={{
                endAdornment: <InputAdornment position="end">PLN</InputAdornment>,
              }}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Cena Cennikowa Brutto"
              type="number"
              value={data.base_price_gross}
              onChange={(e) => handleUpdateBrutto(parseFloat(e.target.value) || 0)}
              InputProps={{
                endAdornment: <InputAdornment position="end">PLN</InputAdornment>,
              }}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth>
              <InputLabel>Typ Rabatu</InputLabel>
              <Select
                value={data.discount_type}
                label="Typ Rabatu"
                onChange={(e) => handleChangeTypRabatu(e.target.value as any)}
              >
                <MenuItem value="Procentowo">Procentowo (%)</MenuItem>
                <MenuItem value="Kwotowo">Kwotowo (PLN)</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label={data.discount_type === "Procentowo" ? "Rabat %" : "Rabat PLN"}
              type="number"
              value={data.discount_type === "Procentowo" ? data.discount_pct * 100 : data.discount_amount_net}
              onChange={(e) => handleUpdateRabat(data.discount_type, parseFloat(e.target.value) || 0)}
              InputProps={{
                endAdornment: <InputAdornment position="end">{data.discount_type === "Procentowo" ? "%" : "PLN"}</InputAdornment>,
              }}
            />
          </Grid>
        </Grid>
      </AccordionDetails>
    </Accordion>
  );
}

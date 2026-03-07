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
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import axios from "axios";
import type { V1DataOption } from "../../types";
import { Calendar, Tag } from "lucide-react";

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
  data: V1DataOption;
  expanded: string | false;
  handleChange: (panel: string) => (event: React.SyntheticEvent, isExpanded: boolean) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  handleUpdate: (field: keyof V1DataOption, value: any) => void;
  handleUpdateNetto: (netto: number) => void;
  handleUpdateBrutto: (brutto: number) => void;
  handleChangeTypRabatu: (typ: string) => void;
  handleUpdateRabat: (typ: string, value: number) => void;
}

export default function VehicleDataSection({
  data,
  expanded,
  handleChange,
  handleUpdate,
  handleUpdateNetto,
  handleUpdateBrutto,
  handleChangeTypRabatu,
  handleUpdateRabat,
}: VehicleDataSectionProps) {
  const [engines, setEngines] = useState<EngineOption[]>([]);
  const [bodyTypes, setBodyTypes] = useState<BodyTypeOption[]>([]);

  useEffect(() => {
    axios
      .get<EngineOption[]>("http://127.0.0.1:8000/api/engines")
      .then((res) => setEngines(res.data))
      .catch((err) => console.error("Failed to load engines:", err));

    fetch("http://127.0.0.1:8000/api/body-types")
      .then((r) => r.json())
      .then((data) => { if (Array.isArray(data)) setBodyTypes(data); })
      .catch((err) => console.error("Failed to load body types:", err));
  }, []);

  return (
    <Accordion
      expanded={expanded === "panel1"}
      onChange={handleChange("panel1")}
      defaultExpanded
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
          <Calendar size={20} color="#1e3a8a" />
          Dane Pojazdu
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ p: 3, pt: 4 }}>
        <Grid container spacing={3}>
          {/* IDENTYFIKACJA */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" color="primary" sx={{ mb: 1 }}>
              Identyfikacja pojazdu
            </Typography>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Marka"
              value={data.Marka}
              onChange={(e) => handleUpdate("Marka", e.target.value)}
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Model (DN)"
              value={data.Model.DN}
              onChange={(e) =>
                handleUpdate("Model", { ...data.Model, DN: e.target.value })
              }
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Nadwozie</InputLabel>
              <Select
                value={data.WersjaNadwozia}
                label="Nadwozie"
                onChange={(e) =>
                  handleUpdate("WersjaNadwozia", e.target.value)
                }
              >
              {(() => {
                  // Map HomologacjaSelected → vehicle_class filter
                  const classFilter =
                    data.HomologacjaSelected === "Osobowy" ? "Osobowy"
                    : data.HomologacjaSelected === "Dostawczy" || data.HomologacjaSelected === "Cieżarowy" ? "Dostawczy"
                    : null; // show all if unknown

                  const filtered = classFilter
                    ? bodyTypes.filter((bt) => bt.vehicle_class === classFilter)
                    : bodyTypes;

                  if (filtered.length === 0 && bodyTypes.length === 0) {
                    return <MenuItem disabled>Ładowanie...</MenuItem>;
                  }

                  if (filtered.length === 0) {
                    return <MenuItem disabled>Brak typów nadwozia dla tej homologacji</MenuItem>;
                  }

                  return Object.entries(
                    filtered.reduce<Record<string, BodyTypeOption[]>>((acc, bt) => {
                      (acc[bt.vehicle_class] = acc[bt.vehicle_class] || []).push(bt);
                      return acc;
                    }, {})
                  ).flatMap(([vc, items]) => [
                    <ListSubheader key={vc}>{vc}</ListSubheader>,
                    ...items.map((bt) => (
                      <MenuItem key={bt.id} value={bt.name}>
                        {bt.name}
                      </MenuItem>
                    )),
                  ]);
                })()}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Wersja Wyposażenia"
              value={data.WersjaWyposazenia}
              onChange={(e) =>
                handleUpdate("WersjaWyposazenia", e.target.value)
              }
              size="small"
            />
          </Grid>

          {/* PARAMETRY TECHNICZNE */}
          <Grid item xs={12} sx={{ mt: 2 }}>
            <Typography variant="subtitle2" color="primary" sx={{ mb: 1 }}>
              Parametry techniczne
            </Typography>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Moc silnika (KM)"
              value={data.MocSilnika}
              onChange={(e) => handleUpdate("MocSilnika", e.target.value)}
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Napęd</InputLabel>
              <Select
                value={data.RodzajPaliwa}
                label="Napęd"
                onChange={(e) => handleUpdate("RodzajPaliwa", e.target.value)}
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
            <FormControl fullWidth size="small">
              <InputLabel>Homologacja</InputLabel>
              <Select
                value={data.HomologacjaSelected}
                label="Homologacja"
                onChange={(e) =>
                  handleUpdate("HomologacjaSelected", e.target.value)
                }
              >
                <MenuItem value="Osobowy">Osobowy</MenuItem>
                <MenuItem value="Cieżarowy">Ciężarowy</MenuItem>
                <MenuItem value="Dostawczy">Dostawczy</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              disabled
              fullWidth
              label="Kategoria SAMAR (Auto)"
              value={data.KategoriaSamar || ""}
              size="small"
              sx={{ bgcolor: "#f5f5f5" }}
            />
          </Grid>

          {/* CENA I RABAT */}
          <Grid item xs={12} sx={{ mt: 2 }}>
            <Typography
              variant="subtitle2"
              color="primary"
              sx={{ mb: 1, display: "flex", alignItems: "center", gap: 1 }}
            >
              <Tag size={16} /> Wartość pojazdu bazowego
            </Typography>
          </Grid>

          {/* CENA BAZOWA */}
          <Grid item xs={12} sm={6} md={4}>
            <TextField
              fullWidth
              type="number"
              label="Cena cennikowa Netto"
              value={data.CenaCennikowaNetto ? data.CenaCennikowaNetto.toFixed(2) : ""}
              onChange={(e) =>
                handleUpdateNetto(parseFloat(e.target.value) || 0)
              }
              size="small"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">PLN</InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
            <TextField
              fullWidth
              type="number"
              label="Cena cennikowa Brutto"
              value={data.CenaCennikowa ? data.CenaCennikowa.toFixed(2) : ""}
              onChange={(e) =>
                handleUpdateBrutto(parseFloat(e.target.value) || 0)
              }
              size="small"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">PLN</InputAdornment>
                ),
              }}
            />
          </Grid>

          {/* PUSTY BLOK DLA WYRÓWNANIA */}
          <Grid item xs={12} sm={12} md={4} />

          {/* RABAT WARTOŚĆ BAZOWA */}
          <Grid item xs={12} sm={4} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Typ rabatu</InputLabel>
              <Select
                value={data.TypRabatu}
                label="Typ rabatu"
                onChange={(e) => handleChangeTypRabatu(e.target.value)}
              >
                <MenuItem value="Procentowo">Procentowo (%)</MenuItem>
                <MenuItem value="Kwotowo">Kwotowo (PLN Brutto)</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={4} md={3}>
            <TextField
              fullWidth
              type="number"
              label="Wartość rabatu"
              value={
                data.TypRabatu === "Procentowo"
                  ? (data.RabatProcent * 100).toFixed(2)
                  : data.RabatKwota.toFixed(2)
              }
              onChange={(e) =>
                handleUpdateRabat(
                  data.TypRabatu,
                  parseFloat(e.target.value) || 0,
                )
              }
              size="small"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    {data.TypRabatu === "Procentowo" ? "%" : "PLN"}
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} sm={4} md={3}>
            <TextField
              fullWidth
              disabled
              label="Kwota rabatu Netto (podgląd)"
              value={data.RabatKwotaNetto?.toFixed(2) || "0.00"}
              size="small"
              sx={{ bgcolor: "#f5f5f5" }}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">PLN</InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} sm={4} md={3}>
             <TextField
              fullWidth
              disabled
              label="Stawka VAT"
              value={(data.StawkaVat * 100).toFixed(0) + "%"}
              size="small"
              sx={{ bgcolor: "#fafafa" }}
             />
          </Grid>
        </Grid>
      </AccordionDetails>
    </Accordion>
  );
}

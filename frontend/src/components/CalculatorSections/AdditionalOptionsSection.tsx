import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Grid,
  FormControlLabel,
  Switch,
  TextField,
  InputAdornment,
  Box,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { Settings2 } from "lucide-react";
import type { V1DataOption } from "../../types";

interface AdditionalOptionsSectionProps {
  data: V1DataOption;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  handleUpdate: (field: keyof V1DataOption, value: any) => void;
}

export default function AdditionalOptionsSection({
  data,
  handleUpdate,
}: AdditionalOptionsSectionProps) {
  return (
    <Accordion
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
          <Settings2 size={20} color="#1e3a8a" />
          Opcje Dodatkowe / Reguły
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ p: 3 }}>
        <Grid container spacing={4}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Typography variant="subtitle2" color="primary" sx={{ mb: 2 }}>
              Ubezpieczenie i Ryzyko
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={data.ExpressPlaciUbezpieczenie}
                    onChange={(e) =>
                      handleUpdate("ExpressPlaciUbezpieczenie", e.target.checked)
                    }
                  />
                }
                label="Express płaci ubezpieczenie"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={data.SamochodZastepczy}
                    onChange={(e) =>
                      handleUpdate("SamochodZastepczy", e.target.checked)
                    }
                  />
                }
                label="Samochód Zastępczy (w pakiecie)"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={data.CzyGPS}
                    onChange={(e) => handleUpdate("CzyGPS", e.target.checked)}
                  />
                }
                label="Urządzenie GPS wymagane"
              />
            </Box>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <Typography variant="subtitle2" color="primary" sx={{ mb: 2 }}>
              Serwisowanie
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={data.CzyUwzgledniaSerwisowanie}
                    onChange={(e) =>
                      handleUpdate("CzyUwzgledniaSerwisowanie", e.target.checked)
                    }
                  />
                }
                label="Uwzględniaj serwisowanie (TR)"
              />

              <Box sx={{ mt: 2, display: "flex", gap: 2 }}>
                <TextField
                  label="Inne Koszty Serwisowania"
                  type="number"
                  size="small"
                  value={data.InneKosztySerwisowania}
                  onChange={(e) =>
                    handleUpdate(
                      "InneKosztySerwisowania",
                      parseFloat(e.target.value) || 0,
                    )
                  }
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">PLN/mc</InputAdornment>
                    ),
                  }}
                />
              </Box>
            </Box>
          </Grid>
        </Grid>
      </AccordionDetails>
    </Accordion>
  );
}

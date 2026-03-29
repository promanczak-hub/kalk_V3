import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Grid,
  TextField,
  IconButton,
  Button,
  Box,
  Divider,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { Plus, Trash2, Package, Wrench } from "lucide-react";
import type { FactoryOption, ServiceOption } from "../../types";

interface AdditionalOptionsSectionProps {
  factoryOptions: FactoryOption[];
  serviceOptions: ServiceOption[];
  addFactoryOption: () => void;
  removeFactoryOption: (id: number) => void;
  addServiceOption: () => void;
  removeServiceOption: (id: number) => void;
  handleUpdate: (field: any, value: any) => void;
  expanded?: boolean;
  onToggle?: (expanded: boolean) => void;
}

export default function AdditionalOptionsSection({
  factoryOptions,
  serviceOptions,
  addFactoryOption,
  removeFactoryOption,
  addServiceOption,
  removeServiceOption,
  handleUpdate,
  expanded = false,
  onToggle,
}: AdditionalOptionsSectionProps) {

  const updateOption = (type: 'factory' | 'service', id: number, field: string, value: any) => {
    const list = type === 'factory' ? factoryOptions : serviceOptions;
    const updated = list.map(opt => opt.id === id ? { ...opt, [field]: value } : opt);
    handleUpdate(type === 'factory' ? 'factory_options' : 'service_options', updated);
  };

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
              bgcolor: "success.main", 
              color: "white",
              display: "flex",
              alignItems: "center",
              justifyContent: "center"
            }}
          >
            <Plus size={18} />
          </Box>
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, color: "text.primary" }}>
              Opcje Dodatkowe
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Wyposażenie fabryczne i Usługi Dealera
            </Typography>
          </Box>
        </Box>
      </AccordionSummary>
      <AccordionDetails sx={{ p: 4 }}>
        <Grid container spacing={4}>
          {/* OPCJE FABRYCZNE */}
          <Grid item xs={12} md={6}>
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Package size={18} color="#059669" />
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Wyposażenie Fabryczne</Typography>
              </Box>
              <Button 
                startIcon={<Plus size={16} />} 
                onClick={addFactoryOption}
                size="small"
                variant="outlined"
                color="success"
              >
                Dodaj
              </Button>
            </Box>
            
            {factoryOptions.length === 0 && (
              <Box sx={{ py: 4, textAlign: "center", bgcolor: "rgba(0,0,0,0.02)", borderRadius: "8px", border: "1px dashed rgba(0,0,0,0.1)" }}>
                <Typography variant="body2" color="text.secondary">Brak dodanych opcji fabrycznych</Typography>
              </Box>
            )}

            {factoryOptions.map((opt) => (
              <Box key={opt.id} sx={{ mb: 2, p: 2, bgcolor: "rgba(0,0,0,0.01)", borderRadius: "8px", border: "1px solid rgba(0,0,0,0.03)" }}>
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      size="small"
                      label="Nazwa opcji"
                      value={opt.name}
                      onChange={(e) => updateOption('factory', opt.id, 'name', e.target.value)}
                    />
                  </Grid>
                  <Grid item xs={10} sm={4}>
                    <TextField
                      fullWidth
                      size="small"
                      label="Cena Netto"
                      type="number"
                      value={opt.price_net}
                      onChange={(e) => updateOption('factory', opt.id, 'price_net', parseFloat(e.target.value) || 0)}
                    />
                  </Grid>
                  <Grid item xs={2}>
                    <IconButton color="error" onClick={() => removeFactoryOption(opt.id)}>
                      <Trash2 size={18} />
                    </IconButton>
                  </Grid>
                </Grid>
              </Box>
            ))}
          </Grid>

          <Divider orientation="vertical" flexItem sx={{ display: { xs: "none", md: "block" }, mx: 1 }} />

          {/* USŁUGI SERWISOWE */}
          <Grid item xs={12} md={5.5}>
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Wrench size={18} color="#2563eb" />
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Usługi Dealera / Serwis</Typography>
              </Box>
              <Button 
                startIcon={<Plus size={16} />} 
                onClick={addServiceOption}
                size="small"
                variant="outlined"
                color="primary"
              >
                Dodaj
              </Button>
            </Box>

            {serviceOptions.length === 0 && (
              <Box sx={{ py: 4, textAlign: "center", bgcolor: "rgba(0,0,0,0.02)", borderRadius: "8px", border: "1px dashed rgba(0,0,0,0.1)" }}>
                <Typography variant="body2" color="text.secondary">Brak dodanych usług</Typography>
              </Box>
            )}

            {serviceOptions.map((opt) => (
              <Box key={opt.id} sx={{ mb: 2, p: 2, bgcolor: "rgba(0,0,0,0.01)", borderRadius: "8px", border: "1px solid rgba(0,0,0,0.03)" }}>
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      size="small"
                      label="Nazwa usługi"
                      value={opt.name}
                      onChange={(e) => updateOption('service', opt.id, 'name', e.target.value)}
                    />
                  </Grid>
                  <Grid item xs={10} sm={4}>
                    <TextField
                      fullWidth
                      size="small"
                      label="Cena Netto"
                      type="number"
                      value={opt.price_net}
                      onChange={(e) => updateOption('service', opt.id, 'price_net', parseFloat(e.target.value) || 0)}
                    />
                  </Grid>
                  <Grid item xs={2}>
                    <IconButton color="error" onClick={() => removeServiceOption(opt.id)}>
                      <Trash2 size={18} />
                    </IconButton>
                  </Grid>
                </Grid>
              </Box>
            ))}
          </Grid>
        </Grid>
      </AccordionDetails>
    </Accordion>
  );
}

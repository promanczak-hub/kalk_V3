import {
  Box,
  Container,
  Paper,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Button,
  Grid,
  Breadcrumbs,
  Link,
} from "@mui/material";
import {
  ChevronRight,
  ChevronLeft,
  Settings2,
  CheckCheck,
  CarFront,
  Zap
} from "lucide-react";

import { useCalculator } from "../hooks/useCalculator";
import VehicleSelector from "./components/VehicleSelector";
import OptionsConfigurator from "./components/OptionsConfigurator";
import CalculationSummary from "./components/CalculationSummary";

const STEPS = ["Wybór Pojazdu", "Konfiguracja Opcji", "Podsumowanie"];

export default function ManualCalculator() {
  const {
    vehicle,
    activeStep,
    handleNext,
    handleBack,
    handleReset,
    updateVehicle,
    factoryOptions,
    serviceOptions,
    addFactoryOption,
    removeFactoryOption,
    addServiceOption,
    removeServiceOption,
    calculationResult,
    isCalculating,
    calculate,
  } = useCalculator();

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0:
        return <VehicleSelector vehicle={vehicle} onUpdate={updateVehicle} />;
      case 1:
        return (
          <OptionsConfigurator
            factoryOptions={factoryOptions}
            serviceOptions={serviceOptions}
            onAddFactory={addFactoryOption}
            onRemoveFactory={removeFactoryOption}
            onAddService={addServiceOption}
            onRemoveService={removeServiceOption}
          />
        );
      case 2:
        return <CalculationSummary result={calculationResult} isLoading={isCalculating} onRecalculate={calculate} />;
      default:
        return "Błąd kroku";
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Breadcrumbs aria-label="breadcrumb">
          <Link underline="hover" color="inherit" href="/">Start</Link>
          <Typography color="text.primary">Kalkulator Ręczny</Typography>
        </Breadcrumbs>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2 }}>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 800, color: "text.primary", display: "flex", alignItems: "center", gap: 2 }}>
              <Box sx={{ p: 1, borderRadius: "12px", bgcolor: "primary.main", color: "white", display: "flex" }}>
                <Zap size={24} />
              </Box>
              Kalkulator Ręczny (V3)
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Szybka symulacja kosztów i raty dla wybranego pojazdu.
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Box sx={{ textAlign: 'right' }}>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>Numer kalkulacji</Typography>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>{vehicle?.calculation_number || "NEW/2026"}</Typography>
            </Box>
          </Box>
        </Box>
      </Box>

      <Paper sx={{ p: 0, borderRadius: "24px", overflow: "hidden", border: "1px solid rgba(0,0,0,0.06)", boxShadow: "0 20px 25px -5px rgba(0,0,0,0.1)" }}>
        <Box sx={{ p: 4, bgcolor: "rgba(0,0,0,0.02)", borderBottom: "1px solid rgba(0,0,0,0.06)" }}>
          <Stepper activeStep={activeStep} alternativeLabel>
            {STEPS.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
        </Box>

        <Box sx={{ p: 4 }}>
          {renderStepContent(activeStep)}
        </Box>

        <Box sx={{ p: 4, bgcolor: "rgba(0,0,0,0.02)", borderTop: "1px solid rgba(0,0,0,0.06)", display: "flex", justifyContent: "space-between" }}>
          <Button
            disabled={activeStep === 0}
            onClick={handleBack}
            startIcon={<ChevronLeft size={18} />}
            sx={{ borderRadius: "12px", px: 3 }}
          >
            Wstecz
          </Button>
          
          <Box sx={{ display: 'flex', gap: 2 }}>
            {activeStep === STEPS.length - 1 ? (
              <Button
                variant="contained"
                onClick={handleReset}
                sx={{ borderRadius: "12px", px: 4, fontWeight: 600 }}
              >
                Nowa Kalkulacja
              </Button>
            ) : (
              <Button
                variant="contained"
                onClick={handleNext}
                endIcon={<ChevronRight size={18} />}
                sx={{ 
                  borderRadius: "12px", 
                  px: 4, 
                  fontWeight: 600,
                  boxShadow: "0 10px 15px -3px rgba(34, 197, 94, 0.3)"
                }}
              >
                Dalej
              </Button>
            )}
          </Box>
        </Box>
      </Paper>

      {/* QUICK STATS FOOTER */}
      {activeStep < 2 && (
        <Grid container spacing={2} sx={{ mt: 3 }}>
          <Grid size={{ xs: 12, sm: 4 }}>
            <Box sx={{ p: 2.5, bgcolor: "white", borderRadius: "20px", border: "1px solid rgba(0,0,0,0.06)", display: "flex", alignItems: "center", gap: 2 }}>
              <Box sx={{ p: 1, borderRadius: "10px", bgcolor: "rgba(59, 130, 246, 0.1)", color: "primary.main" }}>
                <CarFront size={20} />
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Wybrany Okres</Typography>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{vehicle.duration_months} m-cy</Typography>
              </Box>
            </Box>
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <Box sx={{ p: 2.5, bgcolor: "white", borderRadius: "20px", border: "1px solid rgba(0,0,0,0.06)", display: "flex", alignItems: "center", gap: 2 }}>
              <Box sx={{ p: 1, borderRadius: "10px", bgcolor: "rgba(16, 185, 129, 0.1)", color: "success.main" }}>
                <Settings2 size={20} />
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Opcje</Typography>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{factoryOptions.length + serviceOptions.length} dodanych</Typography>
              </Box>
            </Box>
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <Box sx={{ p: 2.5, bgcolor: "white", borderRadius: "20px", border: "1px solid rgba(0,0,0,0.06)", display: "flex", alignItems: "center", gap: 2 }}>
              <Box sx={{ p: 1, borderRadius: "10px", bgcolor: "rgba(245, 158, 11, 0.1)", color: "warning.main" }}>
                <CheckCheck size={20} />
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Stan</Typography>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Gotowy</Typography>
              </Box>
            </Box>
          </Grid>
        </Grid>
      )}
    </Container>
  );
}

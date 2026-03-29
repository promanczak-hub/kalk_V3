import React from "react";
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
  Divider,
} from "@mui/material";
import { 
  ChevronRight, 
  ChevronLeft, 
  Settings2, 
  CheckCheck, 
  Zap, 
  CarFront, 
  Layers 
} from "lucide-react";

import { useCalculator } from "../../hooks/useCalculator";
import VehicleDataSection from "../CalculatorSections/VehicleDataSection";
import AdditionalOptionsSection from "../CalculatorSections/AdditionalOptionsSection";
import OptionsTablesSection from "../CalculatorSections/OptionsTablesSection";
import CalculationResultsSection from "../CalculatorSections/CalculationResultsSection";

const STEPS = ["Pojazd i Cena", "Opcje i Parametry", "Wynik 12-Kroków"];

export default function ManualCalculator() {
  const [activeStep, setActiveStep] = React.useState(0);
  const {
    vehicle,
    handleUpdate,
    handleUpdateNetto,
    handleUpdateBrutto,
    handleUpdateRabat,
    handleChangeTypRabatu,
    factoryOptions,
    serviceOptions,
    addFactoryOption,
    removeFactoryOption,
    addServiceOption,
    removeServiceOption,
    calculationResult,
    isCalculating,
    calculate,
    expandedPanel,
    handleAccordionChange
  } = useCalculator();

  const handleNext = async () => {
    if (activeStep === 1) {
      await calculate();
    }
    setActiveStep((prev) => prev + 1);
  };

  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
  };

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <Box sx={{ animation: "fadeIn 0.3s ease-out" }}>
            <VehicleDataSection
              data={vehicle}
              expanded={expandedPanel === "panel1"}
              onToggle={(exp) => handleAccordionChange("panel1")(null!, exp)}
              handleUpdate={handleUpdate}
              handleUpdateNetto={handleUpdateNetto}
              handleUpdateBrutto={handleUpdateBrutto}
              handleChangeTypRabatu={handleChangeTypRabatu}
              handleUpdateRabat={handleUpdateRabat}
            />
          </Box>
        );
      case 1:
        return (
          <Box sx={{ animation: "fadeIn 0.3s ease-out" }}>
            <AdditionalOptionsSection
              factoryOptions={factoryOptions}
              serviceOptions={serviceOptions}
              addFactoryOption={addFactoryOption}
              removeFactoryOption={removeFactoryOption}
              addServiceOption={addServiceOption}
              removeServiceOption={removeServiceOption}
              handleUpdate={handleUpdate}
              expanded={expandedPanel === "panel2"}
              onToggle={(exp) => handleAccordionChange("panel2")(null!, exp)}
            />
            <OptionsTablesSection
              data={vehicle}
              handleUpdate={handleUpdate}
              expanded={expandedPanel === "panel3"}
              onToggle={(exp) => handleAccordionChange("panel3")(null!, exp)}
            />
          </Box>
        );
      case 2:
        return (
          <Box sx={{ animation: "fadeIn 0.3s ease-out" }}>
            <CalculationResultsSection 
              result={calculationResult} 
              isCalculating={isCalculating} 
            />
          </Box>
        );
      default:
        return null;
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4, mb: 8 }}>
      <Box sx={{ mb: 4 }}>
        <Breadcrumbs sx={{ mb: 1, color: "text.secondary", fontSize: "0.875rem" }}>
          <Link underline="hover" color="inherit" href="/">Dashboard</Link>
          <Typography color="text.primary">Manual LTR Calculator</Typography>
        </Breadcrumbs>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 800, color: "text.primary", letterSpacing: -0.5 }}>
              Kalkulator Manualny LTR
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Pełny 12-etapowy proces wyceny wynajmu długoterminowego
            </Typography>
          </Box>
          <Box sx={{ display: "flex", gap: 1 }}>
             <Box sx={{ 
               display: "flex", 
               alignItems: "center", 
               gap: 0.5, 
               px: 1.5, 
               py: 0.5, 
               borderRadius: "20px", 
               bgcolor: "rgba(34, 197, 94, 0.1)", 
               color: "#059669",
               fontSize: "0.75rem",
               fontWeight: 600
             }}>
               <Zap size={14} /> SYSTEM V3 FINAL ENGINE
             </Box>
          </Box>
        </Box>
      </Box>

      <Paper 
        elevation={0}
        sx={{ 
          p: 0, 
          borderRadius: "24px", 
          overflow: "hidden", 
          border: "1px solid rgba(0,0,0,0.06)",
          boxShadow: "0 4px 6px -1px rgba(0,0,0,0.01), 0 2px 4px -1px rgba(0,0,0,0.006)"
        }}
      >
        {/* STEPPER HEADER */}
        <Box sx={{ px: 4, py: 4, bgcolor: "rgba(15, 23, 42, 0.02)", borderBottom: "1px solid rgba(0,0,0,0.06)" }}>
          <Stepper activeStep={activeStep} alternativeLabel>
            {STEPS.map((label, index) => (
              <Step key={label}>
                <StepLabel 
                  icon={
                    <Box 
                      sx={{ 
                        width: 32, 
                        height: 32, 
                        borderRadius: "50%", 
                        display: "flex", 
                        alignItems: "center", 
                        justifyContent: "center",
                        bgcolor: activeStep >= index ? "primary.main" : "rgba(15, 23, 42, 0.1)",
                        color: "white",
                        fontSize: "0.75rem",
                        fontWeight: 700,
                        transition: "all 0.3s"
                      }}
                    >
                      {activeStep > index ? <CheckCheck size={18} /> : index + 1}
                    </Box>
                  }
                >
                  <Typography variant="subtitle2" sx={{ 
                    fontWeight: activeStep === index ? 700 : 500,
                    color: activeStep >= index ? "text.primary" : "text.secondary"
                  }}>
                    {label}
                  </Typography>
                </StepLabel>
              </Step>
            ))}
          </Stepper>
        </Box>

        {/* STEP CONTENT */}
        <Box sx={{ p: 4 }}>
          {renderStepContent(activeStep)}
        </Box>

        {/* STEPPER ACTIONS */}
        <Box sx={{ p: 4, pt: 0, display: "flex", justifyContent: "space-between" }}>
          <Button
            disabled={activeStep === 0}
            onClick={handleBack}
            startIcon={<ChevronLeft size={20} />}
            sx={{ borderRadius: "12px", px: 3, fontWeight: 600 }}
          >
            Wróć
          </Button>
          
          {activeStep < STEPS.length - 1 ? (
            <Button
              variant="contained"
              onClick={handleNext}
              endIcon={<ChevronRight size={20} />}
              sx={{ 
                borderRadius: "12px", 
                px: 4, 
                fontWeight: 600,
                boxShadow: "0 10px 15px -3px rgba(59, 130, 246, 0.3)"
              }}
            >
              {activeStep === 1 ? "Przelicz i Kontynuuj" : "Dalej"}
            </Button>
          ) : (
            <Button
              variant="contained"
              color="success"
              onClick={() => setActiveStep(0)}
              startIcon={<Zap size={20} />}
              sx={{ 
                borderRadius: "12px", 
                px: 4, 
                fontWeight: 600,
                boxShadow: "0 10px 15px -3px rgba(34, 197, 94, 0.3)"
              }}
            >
              Nowa Kalkulacja
            </Button>
          )}
        </Box>
      </Paper>

      {/* QUICK STATS FOOTER */}
      {activeStep < 2 && (
        <Grid container spacing={2} sx={{ mt: 3 }}>
          <Grid item xs={12} sm={4}>
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
          <Grid item xs={12} sm={4}>
            <Box sx={{ p: 2.5, bgcolor: "white", borderRadius: "20px", border: "1px solid rgba(0,0,0,0.06)", display: "flex", alignItems: "center", gap: 2 }}>
              <Box sx={{ p: 1, borderRadius: "10px", bgcolor: "rgba(16, 185, 129, 0.1)", color: "success.main" }}>
                <Settings2 size={20} />
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Opcje / Serwis</Typography>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{factoryOptions.length + serviceOptions.length} szt.</Typography>
              </Box>
            </Box>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Box sx={{ p: 2.5, bgcolor: "white", borderRadius: "20px", border: "1px solid rgba(0,0,0,0.06)", display: "flex", alignItems: "center", gap: 2 }}>
              <Box sx={{ p: 1, borderRadius: "10px", bgcolor: "rgba(245, 158, 11, 0.1)", color: "warning.main" }}>
                <Layers size={20} />
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Przebieg Roczny</Typography>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>{vehicle.annual_mileage.toLocaleString()} km</Typography>
              </Box>
            </Box>
          </Grid>
        </Grid>
      )}

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </Container>
  );
}

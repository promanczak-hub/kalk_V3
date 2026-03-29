import { useState, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Stack,
  Stepper,
  Step,
  StepLabel,
  StepConnector,
  stepConnectorClasses,
  styled,
  Button,
  Divider,
} from '@mui/material';
import {
  LayoutDashboard,
  Calculator as CalcIcon,
  ChevronRight,
  ChevronLeft,
  Zap,
} from 'lucide-react';
import { useCalculator } from '../../hooks/useCalculator';
import VehicleDataSection from '../CalculatorSections/VehicleDataSection';
import AdditionalOptionsSection from '../CalculatorSections/AdditionalOptionsSection';
import OptionsTablesSection from '../CalculatorSections/OptionsTablesSection';
import CalculationSummarySection from '../CalculatorSections/CalculationSummarySection';

// --- Custom Styled Stepper ---
const ColorlibConnector = styled(StepConnector)(({ theme }) => ({
  [`&.${stepConnectorClasses.alternativeLabel}`]: {
    top: 22,
  },
  [`&.${stepConnectorClasses.active}`]: {
    [`& .${stepConnectorClasses.line}`]: {
      background: 'linear-gradient(95deg, #1e3a8a 0%, #3b82f6 50%, #1e3a8a 100%)',
    },
  },
  [`&.${stepConnectorClasses.completed}`]: {
    [`& .${stepConnectorClasses.line}`]: {
      background: 'linear-gradient(95deg, #1e3a8a 0%, #3b82f6 50%, #1e3a8a 100%)',
    },
  },
  [`& .${stepConnectorClasses.line}`]: {
    height: 3,
    border: 0,
    backgroundColor: theme.palette.mode === 'dark' ? '#1e293b' : '#e2e8f0',
    borderRadius: 1,
  },
}));

const ColorlibStepIconRoot = styled('div')<{
  active?: boolean;
  completed?: boolean;
}>(({ theme, active, completed }) => ({
  backgroundColor: theme.palette.mode === 'dark' ? '#1e293b' : '#f1f5f9',
  zIndex: 1,
  color: theme.palette.mode === 'dark' ? '#64748b' : '#94a3b8',
  width: 40,
  height: 40,
  display: 'flex',
  borderRadius: '12px',
  justifyContent: 'center',
  alignItems: 'center',
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  border: '2px solid',
  borderColor: 'transparent',
  ...(active && {
    background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
    color: '#fff',
    boxShadow: '0 4px 10px 0 rgba(0,0,0,0.25)',
    transform: 'scale(1.1)',
  }),
  ...(completed && {
    background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
    color: '#fff',
  }),
}));

function ColorlibStepIcon(props: { active?: boolean; completed?: boolean; icon: React.ReactNode }) {
  const { active, completed, icon } = props;
  return (
    <ColorlibStepIconRoot active={active} completed={completed}>
      {icon}
    </ColorlibStepIconRoot>
  );
}

const STEPS = [
  { label: 'Dane Pojazdu', icon: <LayoutDashboard size={18} /> },
  { label: 'Wyposażenie i Opcje', icon: <CalcIcon size={18} /> },
  { label: 'Podsumowanie i Wyniki', icon: <Zap size={18} /> },
];

export default function ManualCalculator() {
  const [activeStep, setActiveStep] = useState(0);
  const calculator = useCalculator();

  const handleNext = () => setActiveStep((prev) => Math.min(prev + 1, STEPS.length - 1));
  const handleBack = () => setActiveStep((prev) => Math.max(prev - 1, 0));

  const stepContent = useMemo(() => {
    switch (activeStep) {
      case 0:
        return (
          <VehicleDataSection
            vehicle={calculator.vehicle}
            mappedData={calculator.mappedData}
            onVehicleChange={calculator.updateVehicle}
            onMappedDataChange={calculator.updateMappedData}
          />
        );
      case 1:
        return (
          <Stack spacing={4}>
            <AdditionalOptionsSection
              factoryOptions={calculator.factoryOptions}
              serviceOptions={calculator.serviceOptions}
              onAddFactoryOption={calculator.addFactoryOption}
              onRemoveFactoryOption={calculator.removeFactoryOption}
              onAddServiceOption={calculator.addServiceOption}
              onRemoveServiceOption={calculator.removeServiceOption}
            />
            <OptionsTablesSection
              factoryOptions={calculator.factoryOptions}
              serviceOptions={calculator.serviceOptions}
              onFactoryOptionsChange={calculator.setFactoryOptions}
              onServiceOptionsChange={calculator.setServiceOptions}
            />
          </Stack>
        );
      case 2:
        return (
          <CalculationSummarySection
            result={calculator.calculationResult}
            steps={calculator.steps}
            isCalculating={calculator.isCalculating}
            onRecalculate={calculator.calculate}
          />
        );
      default:
        return null;
    }
  }, [activeStep, calculator]);

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto', py: 4, px: 2 }}>
      {/* Header Area */}
      <Box sx={{ mb: 6, textAlign: 'center' }}>
        <Typography
          variant="h3"
          sx={{
            fontWeight: 900,
            background: 'linear-gradient(45deg, #1e3a8a 30%, #3b82f6 90%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            mb: 1,
            letterSpacing: '-0.02em',
          }}
        >
          Kalkulator Manualny V3
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 700, mx: 'auto' }}>
          Pełny mechanizm 12-stopniowej kalkulacji LTR ze śladem audytowym. 
          Wprowadź dane pojazdu, skonfiguruj opcje i uzyskaj precyzyjny wynik finansowy.
        </Typography>
      </Box>

      {/* Stepper Navigation */}
      <Paper
        elevation={0}
        sx={{
          p: 3,
          mb: 4,
          borderRadius: 4,
          border: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
        }}
      >
        <Stepper
          activeStep={activeStep}
          alternativeLabel
          connector={<ColorlibConnector />}
        >
          {STEPS.map((step, index) => (
            <Step key={step.label}>
              <StepLabel
                StepIconComponent={(props) => (
                  <ColorlibStepIcon {...props} icon={step.icon} />
                )}
              >
                <Typography
                  variant="subtitle2"
                  sx={{
                    fontWeight: activeStep === index ? 700 : 500,
                    color: activeStep === index ? 'primary.main' : 'text.secondary',
                    mt: 1,
                  }}
                >
                  {step.label}
                </Typography>
              </StepLabel>
            </Step>
          ))}
        </Stepper>
      </Paper>

      {/* Main Content Area */}
      <Box sx={{ minHeight: 600 }}>
        {stepContent}
      </Box>

      {/* Footer Navigation */}
      <Divider sx={{ my: 4 }} />
      <Box sx={{ display: 'flex', justifyContent: 'space-between', pb: 8 }}>
        <Button
          variant="outlined"
          startIcon={<ChevronLeft size={18} />}
          onClick={handleBack}
          disabled={activeStep === 0}
          sx={{ borderRadius: 2, px: 3 }}
        >
          Wstecz
        </Button>
        
        {activeStep < STEPS.length - 1 ? (
          <Button
            variant="contained"
            endIcon={<ChevronRight size={18} />}
            onClick={handleNext}
            sx={{ borderRadius: 2, px: 4, fontWeight: 700 }}
          >
            Dalej
          </Button>
        ) : (
          <Button
            variant="contained"
            color="success"
            startIcon={<Zap size={18} />}
            onClick={calculator.calculate}
            disabled={calculator.isCalculating}
            sx={{ 
              borderRadius: 2, 
              px: 4, 
              fontWeight: 700,
              background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
              '&:hover': {
                background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
              }
            }}
          >
            Przelicz Ponownie
          </Button>
        )}
      </Box>
    </Box>
  );
}

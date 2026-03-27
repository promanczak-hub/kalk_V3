import React, { useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, Box, TextField, Stepper, Step, StepLabel,
  MenuItem, Typography, CircularProgress,
} from '@mui/material';
import { PricingPanel } from './PricingPanel';
import type { PricingState, PricingResult } from './types';
import { DEFAULT_PRICING_COMPONENTS } from './types';
import { apiClient } from '../lib/apiClient';

const STEPS = ['Dane pojazdu', 'Panel cenowy'];

const FUEL_TYPES = ['Benzyna', 'Diesel', 'Hybryda', 'Hybryda Plug-in', 'Elektryczny', 'LPG', 'Inne'];
const BODY_TYPES = ['Sedan', 'Kombi', 'Hatchback', 'SUV', 'Crossover', 'Coupe', 'Cabrio', 'Van', 'Inne'];

interface VehicleFormState {
  brand: string;
  model: string;
  version: string;
  fuel: string;
  body_type: string;
  engine_name: string;
  samar_category: string;
  rok: string;
  okres_bazowy: string;
  przebieg_bazowy: string;
}

interface CreateManualModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (id: string) => void;
}

export const CreateManualModal: React.FC<CreateManualModalProps> = ({ open, onClose, onCreated }) => {
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [vehicle, setVehicle] = useState<VehicleFormState>({
    brand: '', model: '', version: '', fuel: '', body_type: '',
    engine_name: '', samar_category: '', rok: '',
    okres_bazowy: '48', przebieg_bazowy: '140000',
  });
  const [pricing, setPricing] = useState<PricingState>({
    components: DEFAULT_PRICING_COMPONENTS.map((c) => ({ ...c })),
    discount_pct: 0,
  });

  const vehicleValid = vehicle.brand.trim().length > 0 && vehicle.model.trim().length > 0;

  const handleVehicleChange = (field: keyof VehicleFormState) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setVehicle((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handlePricingSave = (result: PricingResult) => {
    setPricing({ components: result.components, discount_pct: result.discount_pct });
  };

  const handleSubmit = async () => {
    setSaving(true);
    try {
      const payload = {
        brand: vehicle.brand.trim(),
        model: vehicle.model.trim(),
        version: vehicle.version.trim(),
        fuel: vehicle.fuel,
        body_type: vehicle.body_type,
        engine_name: vehicle.engine_name.trim(),
        samar_category: vehicle.samar_category.trim(),
        rok: vehicle.rok ? parseInt(vehicle.rok, 10) : null,
        okres_bazowy: parseInt(vehicle.okres_bazowy, 10) || 48,
        przebieg_bazowy: parseInt(vehicle.przebieg_bazowy, 10) || 140000,
        pricing: { components: pricing.components, discount_pct: pricing.discount_pct },
      };
      const res = await apiClient.fetch('/api/kalkulacje/manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }) as unknown as { id: string };
      onCreated(res.id);
      handleReset();
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setStep(0);
    setVehicle({ brand: '', model: '', version: '', fuel: '', body_type: '', engine_name: '', samar_category: '', rok: '', okres_bazowy: '48', przebieg_bazowy: '140000' });
    setPricing({ components: DEFAULT_PRICING_COMPONENTS.map((c) => ({ ...c })), discount_pct: 0 });
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleReset} maxWidth="md" fullWidth>
      <DialogTitle sx={{ pb: 1 }}>Nowa kalkulacja manualna</DialogTitle>

      <Box sx={{ px: 3, pb: 1 }}>
        <Stepper activeStep={step} alternativeLabel>
          {STEPS.map((label) => (
            <Step key={label}><StepLabel>{label}</StepLabel></Step>
          ))}
        </Stepper>
      </Box>

      <DialogContent dividers sx={{ pt: 2 }}>
        {step === 0 && (
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
            <TextField label="Marka *" value={vehicle.brand} onChange={handleVehicleChange('brand')} required />
            <TextField label="Model *" value={vehicle.model} onChange={handleVehicleChange('model')} required />
            <TextField label="Wersja wyposażenia" value={vehicle.version} onChange={handleVehicleChange('version')} />
            <TextField label="Silnik" value={vehicle.engine_name} onChange={handleVehicleChange('engine_name')} />
            <TextField select label="Typ paliwa" value={vehicle.fuel} onChange={handleVehicleChange('fuel')}>
              <MenuItem value=""><em>— wybierz —</em></MenuItem>
              {FUEL_TYPES.map((f) => <MenuItem key={f} value={f}>{f}</MenuItem>)}
            </TextField>
            <TextField select label="Typ nadwozia" value={vehicle.body_type} onChange={handleVehicleChange('body_type')}>
              <MenuItem value=""><em>— wybierz —</em></MenuItem>
              {BODY_TYPES.map((b) => <MenuItem key={b} value={b}>{b}</MenuItem>)}
            </TextField>
            <TextField label="Klasa SAMAR" value={vehicle.samar_category} onChange={handleVehicleChange('samar_category')} />
            <TextField label="Rok produkcji" type="number" value={vehicle.rok} onChange={handleVehicleChange('rok')}
              inputProps={{ min: 2015, max: 2030 }} />
            <TextField label="Okres bazowy (mies.)" type="number" value={vehicle.okres_bazowy}
              onChange={handleVehicleChange('okres_bazowy')} inputProps={{ min: 12, max: 84 }} />
            <TextField label="Przebieg bazowy (km)" type="number" value={vehicle.przebieg_bazowy}
              onChange={handleVehicleChange('przebieg_bazowy')} inputProps={{ min: 10000, step: 10000 }} />
          </Box>
        )}

        {step === 1 && (
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Ustaw składowe cenowe. Sumy obliczane są automatycznie — nie możesz ich ręcznie edytować.
            </Typography>
            <PricingPanel
              initialState={pricing}
              embedMode
              onSave={handlePricingSave}
            />
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={handleReset} disabled={saving}>Anuluj</Button>
        {step > 0 && (
          <Button onClick={() => setStep((s) => s - 1)} disabled={saving}>Wstecz</Button>
        )}
        {step < STEPS.length - 1 ? (
          <Button variant="contained" onClick={() => setStep((s) => s + 1)} disabled={!vehicleValid}>
            Dalej
          </Button>
        ) : (
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={saving || !vehicleValid}
            startIcon={saving ? <CircularProgress size={16} /> : null}
          >
            {saving ? 'Tworzenie…' : 'Utwórz kalkulację'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

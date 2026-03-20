import React, { useState, useCallback, useMemo } from 'react';
import {
  Box, Typography, TextField, Checkbox,
  Divider, Button, IconButton, Tooltip, Paper, Stack,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import SaveIcon from '@mui/icons-material/Save';
import type { PricingComponent, PricingState, PricingResult } from './types';
import { apiClient } from "../lib/apiClient";

const VAT_RATE = 0.23;

const fmt = (val: number) =>
  val.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function computeResult(state: PricingState): PricingResult {
  const discountable = state.components
    .filter((c) => !c.no_discount)
    .reduce((s, c) => s + c.amount_net, 0);
  const nonDiscountable = state.components
    .filter((c) => c.no_discount)
    .reduce((s, c) => s + c.amount_net, 0);
  const totalSumNet = discountable + nonDiscountable;
  const discountAmount = Math.round(discountable * state.discount_pct) / 100;
  const purchasePriceNet = Math.round((discountable - discountAmount + nonDiscountable) * 100) / 100;
  const vatAmount = Math.round(purchasePriceNet * VAT_RATE * 100) / 100;
  return {
    components: state.components,
    discount_pct: state.discount_pct,
    discountable_sum: Math.round(discountable * 100) / 100,
    non_discountable_sum: Math.round(nonDiscountable * 100) / 100,
    total_sum_net: Math.round(totalSumNet * 100) / 100,
    discount_amount: discountAmount,
    purchase_price_net: purchasePriceNet,
    vat_amount: vatAmount,
    purchase_price_gross: Math.round((purchasePriceNet + vatAmount) * 100) / 100,
  };
}

interface PricingPanelProps {
  initialState: PricingState;
  kalkulacjaId?: string;
  onSave?: (result: PricingResult) => void;
  /** Jeśli true — nie renderuje przycisku "Zatwierdź i przelicz LTR" */
  embedMode?: boolean;
}

export const PricingPanel: React.FC<PricingPanelProps> = ({
  initialState,
  kalkulacjaId,
  onSave,
  embedMode = false,
}) => {
  const [state, setState] = useState<PricingState>(initialState);
  const [saving, setSaving] = useState(false);

  const result = useMemo(() => computeResult(state), [state]);

  const updateComponent = useCallback(
    (idx: number, field: keyof PricingComponent, value: string | number | boolean) => {
      setState((prev) => {
        const updated = [...prev.components];
        updated[idx] = { ...updated[idx], [field]: value };
        return { ...prev, components: updated };
      });
    },
    [],
  );

  const addComponent = useCallback(() => {
    setState((prev) => ({
      ...prev,
      components: [
        ...prev.components,
        { label: 'Nowa składowa', amount_net: 0, no_discount: false },
      ],
    }));
  }, []);

  const removeComponent = useCallback((idx: number) => {
    setState((prev) => ({
      ...prev,
      components: prev.components.filter((_, i) => i !== idx),
    }));
  }, []);

  const handleSave = useCallback(async () => {
    if (embedMode) {
      onSave?.(result);
      return;
    }
    if (!kalkulacjaId) return;
    setSaving(true);
    try {
      const { apiFetch } = await import('../lib/api');
      await apiClient.fetch(`/api/kalkulacje/${kalkulacjaId}/pricing`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          components: state.components,
          discount_pct: state.discount_pct,
        }),
      });
      onSave?.(result);
    } finally {
      setSaving(false);
    }
  }, [embedMode, kalkulacjaId, state, result, onSave]);

  const rowSx = {
    display: 'grid',
    gridTemplateColumns: '1fr 160px 160px auto',
    alignItems: 'center',
    gap: 1,
    py: 0.75,
  };

  const headerSx = { ...rowSx, py: 0.5, borderBottom: '2px solid', borderBottomColor: 'divider' };

  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, bgcolor: '#fafbff' }}>
      <Typography variant="subtitle2" gutterBottom>
        Panel Cenowy
      </Typography>

      {/* Header */}
      <Box sx={headerSx}>
        <Typography variant="caption" color="text.secondary" fontWeight={600}>Składowa</Typography>
        <Typography variant="caption" color="text.secondary" fontWeight={600} textAlign="right">Kwota netto</Typography>
        <Typography variant="caption" color="text.secondary" fontWeight={600} textAlign="center">Wyłącz z rabatu</Typography>
        <Box />
      </Box>

      {/* Edytowalne wiersze */}
      {state.components.map((comp, idx) => (
        <Box key={idx} sx={rowSx}>
          <TextField
            size="small"
            value={comp.label}
            onChange={(e) => updateComponent(idx, 'label', e.target.value)}
            sx={{ '& input': { fontSize: '0.82rem' } }}
          />
          <TextField
            size="small"
            type="number"
            value={comp.amount_net}
            onChange={(e) => updateComponent(idx, 'amount_net', parseFloat(e.target.value) || 0)}
            inputProps={{ step: 100, min: 0 }}
            sx={{ '& input': { textAlign: 'right', fontSize: '0.82rem' } }}
            InputProps={{ endAdornment: <Typography variant="caption" color="text.secondary">PLN</Typography> }}
          />
          <Box sx={{ display: 'flex', justifyContent: 'center' }}>
            <Checkbox
              size="small"
              checked={comp.no_discount}
              onChange={(e) => updateComponent(idx, 'no_discount', e.target.checked)}
            />
          </Box>
          <Tooltip title="Usuń składową">
            <IconButton size="small" onClick={() => removeComponent(idx)} color="error">
              <DeleteOutlineIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      ))}

      {/* Dodaj składową */}
      <Button
        size="small"
        startIcon={<AddIcon />}
        onClick={addComponent}
        sx={{ mt: 0.5, mb: 1, fontSize: '0.78rem', textTransform: 'none' }}
      >
        Dodaj składową
      </Button>

      <Divider sx={{ my: 1 }} />

      {/* Rabat */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
        <Typography variant="body2" sx={{ flex: 1, fontWeight: 500 }}>
          Rabat (dotyczy składowych rabatowych)
        </Typography>
        <TextField
          size="small"
          type="number"
          value={state.discount_pct}
          onChange={(e) =>
            setState((prev) => ({ ...prev, discount_pct: Math.max(0, Math.min(100, parseFloat(e.target.value) || 0)) }))
          }
          inputProps={{ step: 0.5, min: 0, max: 100 }}
          sx={{ width: 110, '& input': { textAlign: 'right', fontWeight: 600 } }}
          InputProps={{ endAdornment: <Typography variant="caption">%</Typography> }}
        />
      </Box>

      {/* Sekcja obliczonych wartości (NON-EDITABLE) */}
      <Paper
        variant="outlined"
        sx={{ p: 1.5, bgcolor: '#f0f4ff', borderColor: 'primary.light', borderRadius: 1.5 }}
      >
        <Stack spacing={0.5}>
          <ComputedRow label="Σ Suma składowych netto" value={result.total_sum_net} />
          <ComputedRow
            label={`− Rabat ${result.discount_pct}% (od ${fmt(result.discountable_sum)} PLN)`}
            value={-result.discount_amount}
            color="error.main"
          />
          <Divider sx={{ my: 0.5 }} />
          <ComputedRow label="CENA ZAKUPU NETTO ✅" value={result.purchase_price_net} bold primary />
          <ComputedRow label="× VAT 23%" value={result.vat_amount} color="text.secondary" />
          <ComputedRow label="CENA ZAKUPU BRUTTO" value={result.purchase_price_gross} bold />
        </Stack>
      </Paper>

      {!embedMode && (
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={handleSave}
          disabled={saving}
          fullWidth
          sx={{ mt: 2, fontWeight: 600 }}
        >
          {saving ? 'Zapisywanie…' : 'Zatwierdź i przelicz LTR'}
        </Button>
      )}
    </Paper>
  );
};

interface ComputedRowProps {
  label: string;
  value: number;
  bold?: boolean;
  primary?: boolean;
  color?: string;
}

const ComputedRow: React.FC<ComputedRowProps> = ({ label, value, bold, primary, color }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
    <Typography
      variant="body2"
      sx={{ fontWeight: bold ? 700 : 400, color: primary ? 'primary.main' : color ?? 'text.primary', fontSize: '0.82rem' }}
    >
      {label}
    </Typography>
    <Typography
      variant="body2"
      sx={{ fontWeight: bold ? 700 : 500, color: primary ? 'primary.main' : color ?? 'text.primary', fontSize: '0.82rem', fontVariantNumeric: 'tabular-nums' }}
    >
      {fmt(Math.abs(value))} PLN
    </Typography>
  </Box>
);

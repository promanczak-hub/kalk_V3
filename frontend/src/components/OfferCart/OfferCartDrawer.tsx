import React, { useEffect, useRef, useState } from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  List,
  Button,
  Divider,
  TextField,
  Paper,
  Chip,
  MenuItem
} from '@mui/material';
import { X, Trash2, FileOutput, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { useOfferCartStore, type OfferItem, type OfferVariant } from '../../stores/offerCartStore';
import { KalkulacjaParamsRow } from '../../ScoringSearch/components/Results/KalkulacjaParamsRow';

const hasFullCalc = (item: OfferItem): boolean => {
  const cd = item.calculation_data as { kalkulacja_id?: string | null } | null | undefined;
  return !!(cd && cd.kalkulacja_id);
};

const OVERUSE_FEE_OPTIONS: number[] = Array.from({ length: 71 }, (_, i) => Math.round((0.10 + i * 0.01) * 100) / 100);
const DEFAULT_OVERUSE_FEE = 0.50;

const CartItemRecord: React.FC<{
  item: OfferItem;
  onRemove: (id: string) => void;
  onPatch: (id: string, patch: Partial<OfferItem>) => void;
}> = ({ item, onRemove, onPatch }) => {
  const [expanded, setExpanded] = useState(false);
  const overuseFee = item.overuse_fee ?? DEFAULT_OVERUSE_FEE;

  return (
    <Paper sx={{ mb: 2, p: 2, position: 'relative' }} variant="outlined">
      <IconButton 
        size="small" 
        onClick={() => onRemove(item.id)}
        sx={{ position: 'absolute', top: 8, right: 8, color: 'error.main' }}
      >
        <Trash2 size={18} />
      </IconButton>
      
      <Typography variant="subtitle2" fontWeight="bold" sx={{ pr: 4 }}>
        {item.brand} {item.model}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        {item.powertrain}
      </Typography>
      
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1 }}>
        <Chip size="small" label={`${item.term} m-cy`} />
        <Chip size="small" label={`${Math.round((item.term / 12) * item.mileage)} km na kontrakt`} />
        <Chip size="small" label={`Wpłata ${item.contribution}%`} />
        {typeof item.margin_pct === 'number' && (
           <Chip size="small" variant="outlined" color="primary" label={`Marża ${item.margin_pct}%`} />
        )}
        {item.system_recommendation && (
          <Chip size="small" color="success" label={item.system_recommendation} />
        )}
        {hasFullCalc(item) ? (
          <Chip
            size="small"
            color="success"
            variant="outlined"
            icon={<CheckCircle2 size={14} />}
            label="Pełna kalkulacja"
            title="Oferta zawiera VIN, opcje, OC/AC/serwis i podział finansowo-techniczny"
          />
        ) : (
          <Chip
            size="small"
            color="warning"
            variant="outlined"
            icon={<AlertTriangle size={14} />}
            label="Spec z bazy pojazdów"
            title="Pojazd dodano bez wykonanej kalkulacji LTR. Oferta będzie zawierała specyfikację, ale bez VIN, opłaty OC/AC, serwisu, czynszu finansowego/technicznego."
          />
        )}
      </Box>
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
        <Typography variant="h6" color="primary.main">
          {new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' }).format(item.net_installment)} netto/mc
        </Typography>

        {item.variants && item.variants.length > 1 && (
          <Button size="small" onClick={() => setExpanded(!expanded)}>
            {expanded ? 'Ukryj warianty' : 'Pokaż warianty'}
          </Button>
        )}
      </Box>

      {/* Snapshot of the kalkulacja's pricing toggles + financing knobs that
          produced this rate. Frozen at add-to-cart time (kalkulacja_snapshot)
          so the user always sees what was assumed when they quoted this
          offer, even if the underlying calc has been re-priced since. */}
      {item.kalkulacja_snapshot && (
        <Box sx={{ mt: 1 }}>
          <KalkulacjaParamsRow snapshot={item.kalkulacja_snapshot} hideFinancing={false} compact />
        </Box>
      )}

      <Box sx={{ mt: 2, pt: 1, borderTop: '1px dashed', borderColor: 'divider', display: 'flex', flexDirection: 'column', gap: 1 }}>
        <TextField
          select
          size="small"
          label="Opłata za nadprzebieg (zł/km)"
          value={overuseFee}
          onChange={(e) => onPatch(item.id, { overuse_fee: Number(e.target.value) })}
          SelectProps={{ MenuProps: { PaperProps: { style: { maxHeight: 280 } } } }}
        >
          {OVERUSE_FEE_OPTIONS.map((v) => (
            <MenuItem key={v} value={v}>
              {v.toFixed(2)} zł/km
            </MenuItem>
          ))}
        </TextField>
        <TextField
          size="small"
          label="Notatka do tej oferty (np. dostawa za pół roku)"
          multiline
          minRows={2}
          maxRows={4}
          value={item.notes ?? ''}
          onChange={(e) => onPatch(item.id, { notes: e.target.value })}
        />
      </Box>

      {expanded && item.variants && item.variants.length > 0 && (
        <Box sx={{ mt: 2, pt: 1, borderTop: '1px dashed', borderColor: 'divider' }}>
          <Typography variant="caption" color="text.secondary" gutterBottom display="block">
            Alternatywne parametry (marża {item.margin_pct || 0}%):
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mt: 0.5 }}>
            {item.variants
              .filter((v: OfferVariant) => v.monthly_price_net != null && v.found)
              .sort((a: OfferVariant, b: OfferVariant) => ((a.duration_months || 0) - (b.duration_months || 0)) || ((a.annual_mileage || 0) - (b.annual_mileage || 0)))
              .map((v: OfferVariant, idx: number) => {
              const isCurrent = v.duration_months === item.term && v.annual_mileage === item.mileage;
              return (
                <Box 
                  key={idx} 
                  sx={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    p: 0.5,
                    bgcolor: isCurrent ? 'primary.50' : 'transparent',
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: isCurrent ? 'primary.main' : 'divider'
                  }}
                >
                  <Typography variant="caption" sx={{ fontWeight: isCurrent ? 'bold' : 'normal' }}>
                    {v.duration_months} m-cy / {v.annual_mileage} km
                  </Typography>
                  <Typography variant="caption" sx={{ fontWeight: isCurrent ? 'bold' : 'normal', color: isCurrent ? 'primary.main' : 'text.primary' }}>
                    {new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN' }).format(v.monthly_price_net || 0)}
                  </Typography>
                </Box>
              );
            })}
          </Box>
        </Box>
       )}
    </Paper>
  );
};

const OfferCartDrawer: React.FC<{ open: boolean; onClose: () => void }> = ({ open, onClose }) => {
  const { items, clientData, removeItem, updateItem, clearCart, setClientData } = useOfferCartStore();
  const [isGenerating, setIsGenerating] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Pre-warm offer enrichment cache while user fills client data. The backend's
  // _enrich_item runs build_matrix() per item — ~11s on first call, <50ms when
  // cached. Firing preflight on drawer-open + items-change means by the time
  // the user clicks Generate, the enriched payloads are already in Redis.
  // Fire-and-forget: any failure just falls through to the slow path.
  const lastPreflightKey = useRef<string>('');
  useEffect(() => {
    if (!open || items.length === 0) return;
    const key = items.map(i => `${i.id}|${i.term}|${i.mileage}|${i.margin_pct ?? ''}`).join(';');
    if (key === lastPreflightKey.current) return;
    lastPreflightKey.current = key;
    fetch('/api/offers/preflight', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: items.map(item => ({
          ...item,
          id: item.id,
          notes: item.notes ?? '',
          overuse_fee: item.overuse_fee ?? DEFAULT_OVERUSE_FEE,
        })),
      }),
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) console.log('Offer preflight:', data); })
      .catch(err => console.debug('Offer preflight failed (slow path will run on Generate):', err));
  }, [open, items]);

  const handleGenerate = async () => {
    if (items.length === 0) return;
    
    setIsGenerating(true);
    setErrorMsg('');
    try {
      const payload = {
        client_name: clientData.companyName || "Klient Indywidualny",
        client_nip: clientData.nip || "0000000000",
        client_address: clientData.address || "",
        representative: clientData.representative || "",
        items: items.map(item => ({
          ...item,
          id: item.id,
          notes: item.notes ?? "",
          overuse_fee: item.overuse_fee ?? DEFAULT_OVERUSE_FEE,
        }))
      };
      
      console.log('Sending offer generation request:', payload);
      
      const response = await fetch('/api/offers/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error('Offer generation failed');
      }
      const data = await response.json();
      
      // Open the generated Excel file URL
      if (data.url) {
        // Use a hidden anchor to trigger download instead of window.open which might be blocked
        const link = document.createElement('a');
        link.href = data.url;
        link.target = '_blank';
        link.download = '';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        clearCart();
        onClose();
      } else {
        throw new Error('Nierezpoznany format odpowiedzi serwera (brak URL)');
      }
    } catch (error: unknown) {
      console.error(error);
      setErrorMsg('Wystąpił błąd podczas generowania oferty.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <Drawer anchor="right" open={open} onClose={onClose}>
      <Box sx={{ width: 400, display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Koszyk Ofertowy</Typography>
          <IconButton onClick={onClose}><X /></IconButton>
        </Box>
        <Divider />
        
        <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 2 }}>
          {items.length === 0 ? (
            <Typography variant="body2" color="text.secondary">Koszyk jest pusty.</Typography>
          ) : (
            <List>
              {items.map((item) => (
                <CartItemRecord key={item.id} item={item} onRemove={removeItem} onPatch={updateItem} />
              ))}
            </List>
          )}

          {items.length > 0 && (
            <Box sx={{ mt: 4 }}>
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                Dane Klienta (opcjonalne)
              </Typography>
              <TextField
                fullWidth size="small" label="Nazwa Firmy" margin="dense"
                value={clientData.companyName}
                onChange={(e) => setClientData({ companyName: e.target.value })}
              />
              <TextField
                fullWidth size="small" label="NIP" margin="dense"
                value={clientData.nip}
                onChange={(e) => setClientData({ nip: e.target.value })}
              />
              <TextField
                fullWidth size="small" label="Adres" margin="dense"
                value={clientData.address}
                onChange={(e) => setClientData({ address: e.target.value })}
              />
              <TextField
                fullWidth size="small" label="Osoba Reprezentująca" margin="dense"
                value={clientData.representative}
                onChange={(e) => setClientData({ representative: e.target.value })}
              />
            </Box>
          )}
        </Box>

        <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
           {errorMsg && (
            <Typography variant="caption" color="error" sx={{ display: 'block', mb: 1 }}>
              {errorMsg}
            </Typography>
          )}
          <Button
            variant="contained"
            color="primary"
            fullWidth
            startIcon={<FileOutput />}
            disabled={items.length === 0 || isGenerating}
            onClick={handleGenerate}
          >
            {isGenerating ? 'Generowanie...' : 'Generuj Ofertę (XLSX)'}
          </Button>
          <Button
            variant="text"
            color="inherit"
            fullWidth
            sx={{ mt: 1 }}
            disabled={items.length === 0}
            onClick={clearCart}
          >
            Wyczyść Koszyk
          </Button>
        </Box>
      </Box>
    </Drawer>
  );
};

export default OfferCartDrawer;

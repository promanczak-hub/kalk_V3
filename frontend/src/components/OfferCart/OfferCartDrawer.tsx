import React, { useState } from 'react';
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
  Chip
} from '@mui/material';
import { X, Trash2, FileOutput } from 'lucide-react';
import { useOfferCartStore, type OfferItem, type OfferVariant } from '../../stores/offerCartStore';

const CartItemRecord: React.FC<{ item: OfferItem; onRemove: (id: string) => void }> = ({ item, onRemove }) => {
  const [expanded, setExpanded] = useState(false);

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
  const { items, clientData, removeItem, clearCart, setClientData } = useOfferCartStore();
  const [isGenerating, setIsGenerating] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleGenerate = async () => {
    if (items.length === 0) return;
    
    setIsGenerating(true);
    setErrorMsg('');
    try {
      const response = await fetch('/api/offers/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_company: clientData.companyName,
          client_nip: clientData.nip,
          client_address: clientData.address,
          client_representative: clientData.representative,
          items: items.map(item => ({
            ...item,
            id: item.id
          }))
        })
      });

      if (!response.ok) {
        throw new Error('Offer generation failed');
      }
      const data = await response.json();
      
      // Open the generated Excel file URL
      if (data.url) {
        window.open(data.url, '_blank');
        clearCart();
        onClose();
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
                <CartItemRecord key={item.id} item={item} onRemove={removeItem} />
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

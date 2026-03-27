import React from 'react';
import {
  Box, Card, CardContent, Typography, Chip, IconButton,
  Tooltip, Stack, Button, CircularProgress
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditIcon from '@mui/icons-material/Edit';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import type { KalkulacjaListItem } from './types';
import { useOfferCartStore } from '../stores/offerCartStore';
import { apiClient } from '../lib/apiClient';
import { useState } from 'react';

const SOURCE_CONFIG = {
  manual: { label: 'MANUALNA', color: 'secondary' as const },
  clone: { label: 'KOPIA', color: 'warning' as const },
  pdf: { label: 'PDF', color: 'default' as const },
};

const STATUS_COLOR: Record<string, 'default' | 'info' | 'success' | 'error'> = {
  szkic_vertex: 'default',
  w_opracowaniu: 'info',
  gotowa: 'success',
  wyslana: 'success',
  archiwum: 'error',
};

interface KalkulacjaCardProps {
  item: KalkulacjaListItem;
  onClone: (id: string) => void;
  onDelete: (id: string) => void;
  onEditPricing: (id: string) => void;
}

export const KalkulacjaCard: React.FC<KalkulacjaCardProps> = ({
  item, onClone, onDelete, onEditPricing,
}) => {
  const src = item.source ?? 'pdf';
  const srcCfg = SOURCE_CONFIG[src] ?? SOURCE_CONFIG.pdf;
  const statusColor = STATUS_COLOR[item.status] ?? 'default';
  const createdDate = new Date(item.created_at).toLocaleDateString('pl-PL');

  const addToCart = useOfferCartStore(state => state.addItem);
  const [isLoadingSmart, setIsLoadingSmart] = useState(false);

  const handleAddSmartVariants = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsLoadingSmart(true);
    try {
      const res = await apiClient.fetch(`/api/kalkulacje/${item.id}/smart-advisor`, { method: 'POST' });
      const variants = await res.json();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      variants.forEach((v: any) => {
        addToCart({
          id: crypto.randomUUID(),
          brand: v.brand || item.dane_pojazdu?.split(' ')[0] || 'Nieznane',
          model: v.model || '',
          powertrain: v.powertrain || item.fuel_type || '',
          vin_or_config: v.vin_or_config || item.numer_kalkulacji || 'Brak',
          term: v.term || 0,
          mileage: v.mileage || 0,
          net_installment: v.net_installment || 0,
          contribution: 0,
          system_recommendation: `Smart Advisor: ${v.variant_type}`,
          standard_equipment: [],
          factory_options: [],
          dealer_options: [],
          calculation_data: v.calculation_data || {},
        });
      });
    } catch (error) {
      console.error("Error fetching smart variants:", error);
    } finally {
      setIsLoadingSmart(false);
    }
  };

  return (
    <Card
      elevation={0}
      sx={{
        border: '1px solid',
        borderColor: src === 'manual' ? 'secondary.light' : src === 'clone' ? 'warning.light' : 'divider',
        borderRadius: 2,
        transition: 'box-shadow 0.2s',
        '&:hover': { boxShadow: 3 },
      }}
    >
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          {/* Left column */}
          <Box sx={{ flex: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
              <Typography variant="subtitle2" sx={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'text.secondary' }}>
                {item.numer_kalkulacji}
              </Typography>
              <Chip label={srcCfg.label} size="small" color={srcCfg.color} variant="filled"
                sx={{ height: 18, fontSize: '0.65rem', fontWeight: 700 }} />
              <Chip label={item.status.replace(/_/g, ' ').toUpperCase()} size="small"
                color={statusColor} variant="outlined"
                sx={{ height: 18, fontSize: '0.65rem' }} />
            </Box>

            <Typography variant="h6" sx={{ fontSize: '1rem', lineHeight: 1.3 }}>
              {item.dane_pojazdu ?? '—'}
            </Typography>

            <Stack direction="row" spacing={1} sx={{ mt: 0.75, flexWrap: 'wrap' }}>
              {item.fuel && (
                <Chip label={item.fuel} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
              )}
              {item.body_type && (
                <Chip label={item.body_type} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
              )}
              {item.discount_pct != null && item.discount_pct > 0 && (
                <Chip label={`Rabat: ${item.discount_pct}%`} size="small" color="success" variant="outlined"
                  sx={{ fontSize: '0.7rem' }} />
              )}
            </Stack>
          </Box>

          {/* Right column — price + actions */}
          <Box sx={{ textAlign: 'right', ml: 2, flexShrink: 0, minWidth: 160 }}>
            {/* Smart Advisor Widget Button */}
            <Box sx={{ mb: 1.5 }}>
              <Tooltip title="Generuje 3 warianty LTR (Baza, Najniższa Rata, Best Value) i dodaje do koszyka">
                <Button
                  size="small"
                  variant="contained"
                  color="secondary"
                  onClick={handleAddSmartVariants}
                  disabled={isLoadingSmart}
                  startIcon={isLoadingSmart ? <CircularProgress size={14} color="inherit" /> : <AutoAwesomeIcon sx={{ fontSize: '14px !important' }} />}
                  sx={{ fontSize: '0.65rem', textTransform: 'none', py: 0.25, px: 1, borderRadius: 1.5, boxShadow: 'none' }}
                >
                  {isLoadingSmart ? "Analizuję..." : "Smart Pakiet (3 opcje)"}
                </Button>
              </Tooltip>
            </Box>

            {item.cena_netto != null && item.cena_netto > 0 && (
              <Box sx={{ mb: 1 }}>
                <Typography variant="caption" color="text.secondary" display="block">Cena zakupu</Typography>
                <Typography variant="body1" sx={{ fontWeight: 700, color: 'primary.main' }}>
                  {item.cena_netto.toLocaleString('pl-PL', { maximumFractionDigits: 0 })} PLN netto
                </Typography>
              </Box>
            )}
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
              {createdDate}
            </Typography>
            <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
              <Tooltip title="Edytuj panel cenowy">
                <IconButton size="small" onClick={() => onEditPricing(item.id)} color="primary">
                  <EditIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title="Klonuj kalkulację">
                <IconButton size="small" onClick={() => onClone(item.id)}>
                  <ContentCopyIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title="Usuń kalkulację">
                <IconButton size="small" onClick={() => onDelete(item.id)} color="error">
                  <DeleteOutlineIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

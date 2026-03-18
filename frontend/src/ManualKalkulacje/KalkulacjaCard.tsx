import React from 'react';
import {
  Box, Card, CardContent, Typography, Chip, IconButton,
  Tooltip, Stack,
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditIcon from '@mui/icons-material/Edit';
import type { KalkulacjaListItem } from './types';

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
              {item.fuel_type && (
                <Chip label={item.fuel_type} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
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

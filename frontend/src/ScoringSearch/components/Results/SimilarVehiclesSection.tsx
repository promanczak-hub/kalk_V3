import React from 'react';
import { Box, Typography, Skeleton, Chip, useTheme } from '@mui/material';
import type { SimilarVehicle } from '../../hooks/useBatchData';

interface SimilarVehiclesSectionProps {
  vehicleId: string;
  similar?: SimilarVehicle[];
  loading?: boolean;
}

export const SimilarVehiclesSection: React.FC<SimilarVehiclesSectionProps> = ({ vehicleId, similar, loading = false }) => {
  const theme = useTheme();

  if (loading) {
    return (
      <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        <Typography variant="caption" sx={{ color: 'text.secondary', mr: 1, display: 'flex', alignItems: 'center' }}>
          Podobne oferty:
        </Typography>
        <Skeleton variant="rounded" width={80} height={24} />
        <Skeleton variant="rounded" width={80} height={24} />
      </Box>
    );
  }

  if (!similar || similar.length === 0) return null;

  return (
    <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
      <Typography variant="caption" sx={{ color: 'text.secondary', mr: 0.5 }}>
        Podobne oferty ({similar.length}):
      </Typography>
      {similar.map((sim) => (
        <Chip
          key={`sim-${sim.vehicle_id}`}
          size="small"
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Typography variant="caption" sx={{ fontSize: '0.65rem', fontWeight: 500 }}>
                {sim.brand} {sim.model}
              </Typography>
              {sim.best_monthly_price && (
                <Typography variant="caption" sx={{ fontSize: '0.65rem', color: theme.palette.text.secondary }}>
                  od {Number(sim.best_monthly_price).toLocaleString('pl-PL', { maximumFractionDigits: 0 })} PLN
                </Typography>
              )}
            </Box>
          }
          sx={{
            height: 24,
            cursor: 'pointer',
            bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)',
            border: `1px solid ${theme.palette.divider}`,
            '&:hover': {
              bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'
            }
          }}
          onClick={(e) => {
            e.stopPropagation();
            window.open(`/scoring-details/${sim.vehicle_id}`, '_blank');
          }}
        />
      ))}
    </Box>
  );
};

import React from 'react';
import { Box, Typography, Skeleton, Chip, useTheme } from '@mui/material';
import type { SimilarVehicle } from '../../hooks/useBatchData';

interface SimilarVehiclesSectionProps {
  vehicleId: string;
  similar?: SimilarVehicle[];
  loading?: boolean;
}

export const SimilarVehiclesSection: React.FC<SimilarVehiclesSectionProps> = ({ similar, loading = false }) => {
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
    <Box sx={{ mt: 1.5, display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
      <Typography variant="caption" sx={{ color: 'text.secondary', mr: 0.5, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 0.5 }}>
        Alternatywne oferty:
      </Typography>
      {similar.map((sim) => {
        const isHighSim = sim.similarity_score_pct && sim.similarity_score_pct > 80;
        return (
          <Chip
            key={`sim-${sim.vehicle_id}`}
            size="small"
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8 }}>
                <Box sx={{ display: 'flex', flexDirection: 'column', lineHeight: 1 }}>
                  <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600 }}>
                    {sim.brand} {sim.model}
                  </Typography>
                  {sim.similarity_score_pct ? (
                    <Typography 
                      variant="caption" 
                      sx={{ 
                        fontSize: '0.6rem', 
                        color: isHighSim ? theme.palette.success.main : theme.palette.text.secondary,
                        fontWeight: isHighSim ? 700 : 400
                      }}
                    >
                      AI: {sim.similarity_score_pct}%
                    </Typography>
                  ) : null}
                </Box>
                {sim.best_monthly_price && (
                  <Typography variant="caption" sx={{ fontSize: '0.7rem', color: theme.palette.primary.main, fontWeight: 700 }}>
                    od {Number(sim.best_monthly_price).toLocaleString('pl-PL', { maximumFractionDigits: 0 })} PLN
                  </Typography>
                )}
              </Box>
            }
            sx={{
              height: 32,
              px: 0.5,
              cursor: 'pointer',
              bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
              border: `1px solid ${isHighSim ? theme.palette.success.main + '44' : theme.palette.divider}`,
              borderRadius: '6px',
              '&:hover': {
                bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                borderColor: theme.palette.primary.main
              }
            }}
            onClick={(e) => {
              e.stopPropagation();
              window.open(`/scoring-details/${sim.vehicle_id}`, '_blank');
            }}
          />
        );
      })}
    </Box>
  );
};

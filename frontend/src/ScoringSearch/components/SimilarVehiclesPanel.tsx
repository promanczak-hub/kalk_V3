import React from 'react';
import { Box, Typography, Card, CardContent, Chip } from '@mui/material';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import type { SimilarVehicle } from '../hooks/useBatchData';

interface SimilarVehiclesPanelProps {
  vehicles: SimilarVehicle[];
  sourceVehicle: Record<string, any>;
}

const getSimilarityCategory = (source: Record<string, any>, target: SimilarVehicle) => {
  const sourcePrice = Number(source.best_monthly_price || 0);
  const targetPrice = Number(target.best_monthly_price || 0);
  const sourcePower = Number(source.power_hp || 0);
  const targetPower = Number(target.power_hp || 0);

  // 1. Much Cheaper (at least 15% difference)
  if (targetPrice > 0 && sourcePrice > 0 && targetPrice < sourcePrice * 0.85) {
    return { label: 'Znacznie tańszy', color: 'success' as const };
  }

  // 2. More Powerful (at least 20% or 30HP difference)
  if (targetPower > sourcePower && (targetPower >= sourcePower * 1.2 || targetPower > sourcePower + 30)) {
    return { label: 'Większa moc', color: 'info' as const };
  }

  // 3. Different Powertrain (e.g. Electric vs Combustion)
  if (source.fuel && target.fuel && source.fuel !== target.fuel) {
    if (target.fuel.toLowerCase().includes('elektr')) return { label: 'Alternatywa EV', color: 'secondary' as const };
    return { label: 'Inny napęd', color: 'warning' as const };
  }

  // 4. Same Class / Segment (if class matches but brand differs)
  if (target.vehicle_class && source.vehicle_class && target.vehicle_class === source.vehicle_class && target.brand !== source.brand) {
    return { label: 'Ten sam segment', color: 'primary' as const };
  }

  // 5. Slightly Cheaper
  if (targetPrice > 0 && sourcePrice > 0 && targetPrice < sourcePrice) {
    return { label: 'Niższa rata', color: 'success' as const };
  }

  return { label: 'Podobny wybór', color: 'default' as const };
};

export const SimilarVehiclesPanel: React.FC<SimilarVehiclesPanelProps> = ({ vehicles, sourceVehicle }) => {
  if (!vehicles || vehicles.length === 0) {
    return null;
  }

  return (
    <Box sx={{ mt: 3, p: 2, bgcolor: 'rgba(0,0,0,0.015)', borderRadius: 2, border: '1px dashed', borderColor: 'divider' }}>
      <Typography variant="caption" sx={{ mb: 1.5, color: 'text.secondary', display: 'flex', alignItems: 'center', gap: 1, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>
        <DirectionsCarIcon sx={{ fontSize: 16 }} /> Inteligentne Alternatywy AI
      </Typography>
      <Box 
        sx={{ 
          display: 'grid', 
          gridTemplateColumns: {
            xs: 'repeat(1, 1fr)',
            sm: 'repeat(2, 1fr)',
            md: 'repeat(3, 1fr)',
            lg: 'repeat(5, 1fr)'
          },
          gap: 2 
        }}
      >
        {vehicles.map((v) => {
          const category = getSimilarityCategory(sourceVehicle, v);
          return (
            <Card 
              key={v.vehicle_id} 
              sx={{ 
                display: 'flex', 
                flexDirection: 'column', 
                bgcolor: 'background.paper', 
                border: 1, 
                borderColor: 'divider', 
                boxShadow: 'none',
                cursor: 'pointer',
                borderRadius: 1.5,
                transition: 'all 0.2s',
                '&:hover': {
                  borderColor: 'primary.main',
                  transform: 'translateY(-2px)',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.08)'
                }
              }}
              onClick={(e) => {
                e.stopPropagation();
                window.open(`/scoring-details/${v.vehicle_id}`, '_blank');
              }}
            >
              <CardContent sx={{ flexGrow: 1, p: 1.25, '&:last-child': { pb: 1.25 } }}>
                <Box sx={{ mb: 1 }}>
                  <Chip 
                    size="small" 
                    label={category.label} 
                    color={category.color} 
                    sx={{ height: 18, fontSize: '0.6rem', fontWeight: 700, borderRadius: '4px' }} 
                  />
                </Box>
                
                <Typography variant="caption" fontWeight="bold" sx={{ display: 'block', mb: 0.5, lineHeight: 1.2, height: 32, overflow: 'hidden' }}>
                  {v.brand} {v.model}
                </Typography>

                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 'auto', pt: 1, borderTop: '1px solid', borderColor: 'rgba(0,0,0,0.05)' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                    {v.best_monthly_price ? `${v.best_monthly_price.toLocaleString('pl-PL')} zł` : 'Wycena...'}
                  </Typography>
                  {v.similarity_score_pct && (
                    <Typography variant="caption" sx={{ color: 'success.main', fontWeight: 800, fontSize: '0.65rem' }}>
                      {v.similarity_score_pct}%
                    </Typography>
                  )}
                </Box>
              </CardContent>
            </Card>
          );
        })}
      </Box>
    </Box>
  );
};

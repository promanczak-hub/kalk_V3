import React from 'react';
import { Box, Typography, Card, CardContent, Chip, Stack } from '@mui/material';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import type { SimilarVehicle } from '../hooks/useBatchData';

interface SimilarVehiclesPanelProps {
  vehicles: SimilarVehicle[];
}

export const SimilarVehiclesPanel: React.FC<SimilarVehiclesPanelProps> = ({ vehicles }) => {
  if (!vehicles || vehicles.length === 0) {
    return null; /* Hide completely if no similar vehicles instead of showing empty state */
  }

  return (
    <Box sx={{ mt: 3, p: 2, bgcolor: 'rgba(0,0,0,0.02)', borderRadius: 2, border: '1px dashed', borderColor: 'divider' }}>
      <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary', display: 'flex', alignItems: 'center', gap: 1 }}>
        <DirectionsCarIcon fontSize="small" /> Inteligentne Alternatywy (Ta sama klasa)
      </Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ overflowX: 'auto', pb: 1 }}>
        {vehicles.map((v) => (
          <Card 
            key={v.vehicle_id} 
            sx={{ 
              minWidth: 220, 
              flexBasis: '33%', 
              flexShrink: 0, 
              display: 'flex', 
              flexDirection: 'column', 
              bgcolor: 'background.paper', 
              border: 1, 
              borderColor: 'divider', 
              boxShadow: 'none',
              cursor: 'pointer',
              '&:hover': {
                borderColor: 'primary.main',
                boxShadow: 2
              }
            }}
            onClick={(e) => {
              e.stopPropagation();
              window.open(`/scoring-details/${v.vehicle_id}`, '_blank');
            }}
          >
            <CardContent sx={{ flexGrow: 1, p: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Typography variant="body2" fontWeight="bold" noWrap>
                  {v.brand} {v.model}
                </Typography>
                {v.similarity_score_pct && (
                  <Chip size="small" label={`${v.similarity_score_pct}%`} color="success" variant="outlined" sx={{ height: 20, fontSize: '0.65rem' }} />
                )}
              </Box>
              
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1.5 }}>
                 <Typography variant="caption" color="text.secondary">Od:</Typography>
                <Typography variant="subtitle2" fontWeight="bold" color="primary.main">
                  {v.best_monthly_price ? `${v.best_monthly_price.toLocaleString('pl-PL')} PLN` : 'Wycena...'}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        ))}
      </Stack>
    </Box>
  );
};

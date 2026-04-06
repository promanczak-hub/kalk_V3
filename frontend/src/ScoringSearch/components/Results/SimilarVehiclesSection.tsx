import React, { useState } from 'react';
import { Box, Typography, CircularProgress, ToggleButtonGroup, ToggleButton } from '@mui/material';
import LocalOfferIcon from '@mui/icons-material/LocalOffer';
import SpeedIcon from '@mui/icons-material/Speed';
import SecurityIcon from '@mui/icons-material/Security';
import NatureIcon from '@mui/icons-material/Nature';
import WeekendIcon from '@mui/icons-material/Weekend';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';

import { useVehicleAlternatives } from '../../hooks/useBatchData';
import type { SimilarVehicle } from '../../hooks/useBatchData';
import { SimilarVehiclesPanel } from '../SimilarVehiclesPanel';

interface SimilarVehiclesSectionProps {
  vehicleId: string;
  sourceVehicle: Record<string, unknown>;
  targetDuration: number;
  targetAnnualMileage: number;
  similarData?: SimilarVehicle[];
}

type CategoryKey = 'similar' | 'cheaper' | 'stronger' | 'safer' | 'more_comfortable' | 'greener';

export const SimilarVehiclesSection: React.FC<SimilarVehiclesSectionProps> = ({
  vehicleId,
  sourceVehicle,
  targetDuration,
  targetAnnualMileage,
  similarData,
}) => {
  const [category, setCategory] = useState<CategoryKey>('similar');

  const isDeepAI = category !== 'similar';

  const { alternatives, loading } = useVehicleAlternatives(
    vehicleId,
    targetDuration,
    targetAnnualMileage,
    category,
    isDeepAI
  );

  const handleCategoryChange = (
    _event: React.MouseEvent<HTMLElement>,
    newCategory: CategoryKey | null,
  ) => {
    if (newCategory) setCategory(newCategory);
  };

  const displayVehicles = isDeepAI ? alternatives : (similarData || []);

  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="caption" sx={{ mb: 1, display: 'block', fontWeight: 'bold' }}>
        Szukaj alternatyw (Deep AI):
      </Typography>
      <ToggleButtonGroup
        value={category}
        exclusive
        onChange={handleCategoryChange}
        size="small"
        sx={{ flexWrap: 'wrap', mb: 1.5 }}
      >
        <ToggleButton value="similar" sx={{ fontSize: '0.7rem', textTransform: 'none' }}>
          <CompareArrowsIcon sx={{ fontSize: 16, mr: 0.5 }} /> Bliźniaki
        </ToggleButton>
        <ToggleButton value="cheaper" sx={{ fontSize: '0.7rem', textTransform: 'none' }}>
          <LocalOfferIcon sx={{ fontSize: 16, mr: 0.5 }} /> Tańszy
        </ToggleButton>
        <ToggleButton value="stronger" sx={{ fontSize: '0.7rem', textTransform: 'none' }}>
          <SpeedIcon sx={{ fontSize: 16, mr: 0.5 }} /> Mocniejszy
        </ToggleButton>
        <ToggleButton value="safer" sx={{ fontSize: '0.7rem', textTransform: 'none' }}>
          <SecurityIcon sx={{ fontSize: 16, mr: 0.5 }} /> Bezpieczniejszy
        </ToggleButton>
        <ToggleButton value="more_comfortable" sx={{ fontSize: '0.7rem', textTransform: 'none' }}>
          <WeekendIcon sx={{ fontSize: 16, mr: 0.5 }} /> Bardziej komfortowy
        </ToggleButton>
        <ToggleButton value="greener" sx={{ fontSize: '0.7rem', textTransform: 'none' }}>
          <NatureIcon sx={{ fontSize: 16, mr: 0.5 }} /> Bardziej ekologiczny
        </ToggleButton>
      </ToggleButtonGroup>

      {loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CircularProgress size={20} />
          <Typography variant="caption" color="text.secondary">Szukam najlepszych alternatyw...</Typography>
        </Box>
      )}

      {!loading && displayVehicles.length > 0 && (
        <SimilarVehiclesPanel
          vehicles={displayVehicles}
          sourceVehicle={sourceVehicle}
        />
      )}

      {!loading && isDeepAI && displayVehicles.length === 0 && (
        <Typography variant="caption" color="text.secondary">
          Brak odpowiednich alternatyw dla tej kategorii.
        </Typography>
      )}
    </Box>
  );
};

import React from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';

import { useVehicleAlternativesBlend } from '../../hooks/useBatchData';
import type { SimilarVehicle } from '../../hooks/useBatchData';
import { SimilarVehiclesPanel } from '../SimilarVehiclesPanel';
import type { SelectedFeature } from '../../types';

interface SimilarVehiclesSectionProps {
  vehicleId: string;
  sourceVehicle: Record<string, unknown>;
  targetDuration: number;
  targetAnnualMileage: number;
  similarData?: SimilarVehicle[];
  requirements?: SelectedFeature[];
}

export const SimilarVehiclesSection: React.FC<SimilarVehiclesSectionProps> = ({
  vehicleId,
  sourceVehicle,
  targetDuration,
  targetAnnualMileage,
  similarData,
  requirements = [],
}) => {
  const { alternatives, loading } = useVehicleAlternativesBlend(
    vehicleId,
    targetDuration,
    targetAnnualMileage,
    true,
    requirements
  );

  return (
    <Box sx={{ mt: 2 }}>
      {similarData && similarData.length > 0 && (
        <SimilarVehiclesPanel
          vehicles={similarData}
          sourceVehicle={sourceVehicle}
          title="Klasyczne alternatywy (Bliźniaki)"
        />
      )}

      {loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 3, mb: 1 }}>
          <CircularProgress size={20} />
          <Typography variant="caption" color="text.secondary">Badam zróżnicowane opcje (AI)...</Typography>
        </Box>
      )}

      {!loading && alternatives && alternatives.length > 0 && (
        <SimilarVehiclesPanel
          vehicles={alternatives}
          sourceVehicle={sourceVehicle}
          title="Alternatywy Okiem AI (Rekomendacje)"
        />
      )}

      {!loading && (!alternatives || alternatives.length === 0) && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 3 }}>
          Brak odpowiednich alternatyw polecanych przez AI.
        </Typography>
      )}
    </Box>
  );
};

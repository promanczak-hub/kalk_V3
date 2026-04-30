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
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            mt: 3,
            mb: 1,
            p: 1.25,
            bgcolor: '#F8FAFC',
            borderRadius: '8px',
            border: '1px dashed #CBD5E1',
          }}
        >
          <CircularProgress size={16} thickness={5} />
          <Box sx={{ display: 'flex', flexDirection: 'column' }}>
            <Typography variant="caption" sx={{ color: '#475569', fontWeight: 600, fontSize: '0.7rem' }}>
              AI szuka zróżnicowanych alternatyw…
            </Typography>
            <Typography variant="caption" sx={{ color: '#94A3B8', fontSize: '0.6rem' }}>
              Analiza klas SAMAR, opcji wyposażenia i konkurencyjnych marek (~5-15s)
            </Typography>
          </Box>
        </Box>
      )}

      {!loading && alternatives && alternatives.length > 0 && (
        <SimilarVehiclesPanel
          vehicles={alternatives}
          sourceVehicle={sourceVehicle}
          title="Alternatywy Okiem AI (Rekomendacje)"
        />
      )}

    </Box>
  );
};

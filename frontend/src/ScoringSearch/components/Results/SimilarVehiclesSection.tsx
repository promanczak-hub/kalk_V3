import React, { useState } from 'react';
import { Box, Typography } from '@mui/material';
import { ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

import type { SimilarVehicle } from '../../hooks/useBatchData';
import { SimilarVehiclesPanel } from '../SimilarVehiclesPanel';

interface SimilarVehiclesSectionProps {
  vehicleId: string;
  sourceVehicle: Record<string, unknown>;
  targetDuration: number;
  targetAnnualMileage: number;
  similarData?: SimilarVehicle[];
  marginPct?: number;
  matrixActive?: boolean;
}

export const SimilarVehiclesSection: React.FC<SimilarVehiclesSectionProps> = ({
  sourceVehicle,
  similarData,
  marginPct,
  targetDuration,
  targetAnnualMileage,
  matrixActive,
}) => {
  const [expanded, setExpanded] = useState(false);

  const hasSimilar = similarData && similarData.length > 0;

  return (
    <div className="border-t border-slate-200">
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
        className="w-full text-left flex items-center justify-between gap-2 text-xs text-slate-600 hover:bg-slate-50 px-4 py-2.5 transition-colors"
      >
        <span className="font-medium inline-flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-violet-500" />
          {expanded ? 'Ukryj podobne pojazdy' : 'Pokaż podobne pojazdy'}
        </span>
        {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>

      {expanded && (
        <Box sx={{ px: 2, pb: 2 }}>
          {hasSimilar ? (
            <SimilarVehiclesPanel
              vehicles={similarData}
              sourceVehicle={sourceVehicle}
              title="Podobne pojazdy"
              marginPct={marginPct}
              targetDuration={targetDuration}
              targetAnnualMileage={targetAnnualMileage}
              matrixActive={matrixActive}
            />
          ) : (
            <Typography variant="caption" sx={{ color: '#94A3B8', fontStyle: 'italic', display: 'block', py: 1 }}>
              Brak podobnych pojazdów dla tego modelu.
            </Typography>
          )}
        </Box>
      )}
    </div>
  );
};

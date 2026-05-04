import React, { useState } from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';
import { ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

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
  const [expanded, setExpanded] = useState(false);

  // Only fetch AI alternatives when user expands the section
  const { alternatives, loading } = useVehicleAlternativesBlend(
    vehicleId,
    targetDuration,
    targetAnnualMileage,
    expanded, // lazy: only fetch when expanded
    requirements
  );

  const hasSimilar = similarData && similarData.length > 0;
  const hasAlternatives = alternatives && alternatives.length > 0;

  return (
    <div className="border-t border-slate-200">
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
        className="w-full text-left flex items-center justify-between gap-2 text-xs text-slate-600 hover:bg-slate-50 px-4 py-2.5 transition-colors"
      >
        <span className="font-medium inline-flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-violet-500" />
          {expanded ? 'Ukryj alternatywy' : 'Pokaż alternatywy AI'}
        </span>
        {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>

      {expanded && (
        <Box sx={{ px: 2, pb: 2 }}>
          {hasSimilar && (
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
                mt: 1.5,
                p: 1.25,
                bgcolor: '#F8FAFC',
                borderRadius: '8px',
                border: '1px dashed #CBD5E1',
              }}
            >
              <CircularProgress size={16} thickness={5} />
              <Typography variant="caption" sx={{ color: '#475569', fontWeight: 600, fontSize: '0.7rem' }}>
                AI analizuje alternatywy...
              </Typography>
            </Box>
          )}

          {!loading && hasAlternatives && (
            <SimilarVehiclesPanel
              vehicles={alternatives}
              sourceVehicle={sourceVehicle}
              title="Rekomendacje AI"
            />
          )}

          {!loading && !hasSimilar && !hasAlternatives && (
            <Typography variant="caption" sx={{ color: '#94A3B8', fontStyle: 'italic', display: 'block', py: 1 }}>
              Brak alternatyw dla tego pojazdu.
            </Typography>
          )}
        </Box>
      )}
    </div>
  );
};

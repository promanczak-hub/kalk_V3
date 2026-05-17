import React, { useState } from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';
import { ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

import type { SimilarStatus, SimilarVehicle } from '../../hooks/useBatchData';
import { SimilarVehiclesPanel } from '../SimilarVehiclesPanel';

interface SimilarVehiclesSectionProps {
  vehicleId: string;
  sourceVehicle: Record<string, unknown>;
  targetDuration: number;
  targetAnnualMileage: number;
  similarData?: SimilarVehicle[];
  /**
   * Backend zwraca per-pojazd: 'pending' (embeddingi w trakcie generowania —
   * pokazujemy spinner + komunikat „Trwa generowanie..."), 'ready' (lista
   * dopasowań), 'empty' (embeddingi gotowe, ale 0 dopasowań — pokazujemy
   * „Brak podobnych"). Brak wartości = stary backend bez X-Similar-Status →
   * fallback do dotychczasowej logiki (length > 0 ? lista : 'Brak').
   */
  similarStatus?: SimilarStatus;
  marginPct?: number;
  matrixActive?: boolean;
}

export const SimilarVehiclesSection: React.FC<SimilarVehiclesSectionProps> = ({
  sourceVehicle,
  similarData,
  similarStatus,
  marginPct,
  targetDuration,
  targetAnnualMileage,
  matrixActive,
}) => {
  const [expanded, setExpanded] = useState(false);

  const hasSimilar = similarData && similarData.length > 0;
  // Status 'pending' nadpisuje wszystko — nawet jeśli starszy cache zwrócił
  // jakieś dane, ale nowy embedding się generuje, lepiej pokazać spinner
  // niż mylące "0 dopasowań".
  const isPending = similarStatus === 'pending';
  const isEmpty = similarStatus === 'empty' || (!isPending && !hasSimilar);

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
          {isPending ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 1.5 }}>
              <CircularProgress size={14} sx={{ color: '#8B5CF6' }} />
              <Typography variant="caption" sx={{ color: '#64748B', fontStyle: 'italic' }}>
                Trwa generowanie podobnych pojazdów…
              </Typography>
            </Box>
          ) : hasSimilar ? (
            <SimilarVehiclesPanel
              vehicles={similarData}
              sourceVehicle={sourceVehicle}
              title="Podobne pojazdy"
              marginPct={marginPct}
              targetDuration={targetDuration}
              targetAnnualMileage={targetAnnualMileage}
              matrixActive={matrixActive}
            />
          ) : isEmpty ? (
            <Typography variant="caption" sx={{ color: '#94A3B8', fontStyle: 'italic', display: 'block', py: 1 }}>
              Brak podobnych pojazdów dla tego modelu.
            </Typography>
          ) : null}
        </Box>
      )}
    </div>
  );
};

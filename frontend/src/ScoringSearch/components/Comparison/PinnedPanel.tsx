import React from 'react';
import type { ScoredVehicle, VehicleSnapshot } from '../../types';
import { PinnedColumn } from './PinnedColumn';

interface PinnedPanelProps {
  pinnedCars: ScoredVehicle[];
  snapshots: Record<string, VehicleSnapshot>;
  loading: boolean;
  onUnpin: (vehicleId: string) => void;
  onClearAll: () => void;
  onRequestCurve: (vehicleId: string) => void;
}

export const PinnedPanel: React.FC<PinnedPanelProps> = ({
  pinnedCars,
  snapshots,
  loading,
  onUnpin,
  onClearAll,
  onRequestCurve,
}) => {
  if (pinnedCars.length === 0) {
    return (
      <div className="border-t border-slate-200 bg-slate-50 px-4 py-3 text-center text-[12px] text-slate-500">
        Przypnij pojazd klikając w punkt na wykresie, aby zobaczyć dekompozycję kosztów.
      </div>
    );
  }

  return (
    <div className="border-t border-slate-200 bg-slate-50">
      <div className="flex items-center justify-between px-3 py-2">
        <div className="text-[12px] font-semibold text-slate-700">
          Porównanie ({pinnedCars.length}/8)
        </div>
        <button
          onClick={onClearAll}
          className="text-[11px] text-slate-500 hover:text-slate-800 underline-offset-2 hover:underline"
        >
          Wyczyść wszystkie
        </button>
      </div>
      <div className="px-3 pb-3 overflow-x-auto">
        <div className="flex gap-2">
          {pinnedCars.map((car) => (
            <PinnedColumn
              key={car.vehicle_id}
              car={car}
              snapshot={snapshots[car.vehicle_id]}
              loading={loading}
              onClose={() => onUnpin(car.vehicle_id)}
              onRequestCurve={() => onRequestCurve(car.vehicle_id)}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

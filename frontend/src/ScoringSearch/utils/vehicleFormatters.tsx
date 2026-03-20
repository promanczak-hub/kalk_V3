import React from 'react';
import LocalGasStationIcon from '@mui/icons-material/LocalGasStation';
import BoltIcon from '@mui/icons-material/Bolt';

export const fuelIcon = (fuel: string | null) => {
  if (!fuel) return <LocalGasStationIcon sx={{ fontSize: 14 }} />;
  const low = fuel.toLowerCase();
  if (low.includes('elektr') || low.includes('ev') || low.includes('bev'))
    return <BoltIcon sx={{ fontSize: 14 }} />;
  if (low.includes('hybr')) return <BoltIcon sx={{ fontSize: 14 }} />;
  return <LocalGasStationIcon sx={{ fontSize: 14 }} />;
};

export const fuelColor = (fuel: string | null): 'default' | 'success' | 'info' => {
  if (!fuel) return 'default';
  const low = fuel.toLowerCase();
  if (low.includes('elektr') || low.includes('ev') || low.includes('bev')) return 'success';
  if (low.includes('hybr')) return 'info';
  return 'default';
};

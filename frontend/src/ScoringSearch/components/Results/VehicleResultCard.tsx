import React from 'react';
import { Box, Typography, Card, CardContent, Chip, Tooltip, IconButton, Button } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import SpeedIcon from '@mui/icons-material/Speed';
import SettingsIcon from '@mui/icons-material/Settings';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import LocalOfferIcon from '@mui/icons-material/LocalOffer';
import BuildIcon from '@mui/icons-material/Build';

import type { SearchContext } from '../../types';
import type { PriceForParams, SimilarVehicle } from '../../hooks/useBatchData';
import { fuelColor, fuelIcon } from '../../utils/vehicleFormatters';
import { LtrPriceBlock } from './LtrPriceBlock';
import { SimilarVehiclesSection } from './SimilarVehiclesSection';
import { useOfferCartStore } from '../../../stores/offerCartStore';

interface VehicleResultCardProps {
  car: Record<string, unknown>;
  searchContext: SearchContext;
  targetDuration: number;
  targetAnnualMileage: number;
  priceData?: { price_for_params?: PriceForParams, variants?: PriceForParams[] };
  pricesLoading: boolean;
  similarData?: SimilarVehicle[];
  similarLoading: boolean;
}

export const VehicleResultCard: React.FC<VehicleResultCardProps> = ({
  car,
  searchContext,
  targetDuration,
  targetAnnualMileage,
  priceData,
  pricesLoading,
  similarData,
  similarLoading,
}) => {
  const addToCart = useOfferCartStore(state => state.addItem);
  const vehicleId = car.vehicle_id as string;
  const hasSpecs = car.fuel_type || car.power_hp || car.transmission || car.body_style || car.drive_type;
  const matchedFeatures = (car.matched_features || []) as string[];
  const missingFeatures = (car.missing_features || []) as string[];

  const handleAddToCart = (e: React.MouseEvent) => {
    e.stopPropagation();
    const basePrice = (car.best_monthly_price as number) || 0;
    const marginVal = (searchContext.margin_pct || 0) / 100.0;
    const finalPrice = marginVal < 1.0 ? basePrice / (1.0 - marginVal) : basePrice;
    const variantPriceData = priceData?.price_for_params;
    
    addToCart({
      id: crypto.randomUUID(),
      brand: (car.brand as string) || '',
      model: (car.model as string) || '',
      powertrain: (car.fuel_type as string) || '',
      vin_or_config: (car.configuration_code as string) || (car.offer_number as string) || 'Brak',
      term: variantPriceData?.duration_months || targetDuration,
      mileage: variantPriceData?.annual_mileage || targetAnnualMileage,
      net_installment: finalPrice,
      contribution: 0,
      margin_pct: searchContext.margin_pct || 0,
      variants: priceData?.variants || [],
      system_recommendation: typeof car.match_score_pct === 'number' && car.match_score_pct >= 90
        ? 'Najlepsze dopasowanie'
        : undefined,
      standard_equipment: [],
      factory_options: [],
      dealer_options: [],
      calculation_data: car,
    });
  };

  const cleanPrice = (val?: string | null) => val ? val.replace(/netto|brutto|pln/gi, '').trim() : '';

  return (
    <Card elevation={1} sx={{ borderRadius: 2, transition: 'box-shadow 0.2s', '&:hover': { boxShadow: 4 } }}>
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 0.5 }}>
          {/* Left Side: Vehicle Info & Specs */}
          <Box sx={{ flex: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
              <Typography variant="h6" sx={{ lineHeight: 1.2 }}>{car.brand as string} {car.model as string}</Typography>
              {!!car.trim_level && car.trim_level !== 'Brak' && (
                <Chip label={car.trim_level as string} size="small" variant="outlined" color="primary" sx={{ height: 20, fontSize: '0.68rem', fontWeight: 600, borderRadius: '4px' }} />
              )}
              {(!!car.configuration_code || !!car.offer_number) && (
                <Chip label={(car.configuration_code as string) || (car.offer_number as string)} size="small" variant="outlined"
                  sx={{ height: 20, fontSize: '0.68rem', fontWeight: 600, borderRadius: '4px', fontFamily: '"Geist Mono", monospace', color: 'slate.600', borderColor: 'slate.300', bgcolor: 'slate.50' }} />
              )}
              <Tooltip title="Sprawdź rekord w Ekstrakcji Danych">
                <IconButton size="small" href={`/?highlight=${vehicleId}`} target="_blank" sx={{ color: 'text.secondary', ml: 'auto' }}>
                  <OpenInNewIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
            <Typography variant="body2" color="textSecondary" sx={{ mt: 0.25 }}>{car.version as string}</Typography>

            {!!hasSpecs && (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                {!!car.fuel_type && (
                  <Chip icon={fuelIcon(car.fuel_type as string)} label={car.fuel_type as string} size="small"
                    color={fuelColor(car.fuel_type as string)}
                    variant={fuelColor(car.fuel_type as string) !== 'default' ? 'filled' : 'outlined'}
                    sx={{ '& .MuiChip-icon': { fontSize: 14 } }} />
                )}
                {!!car.power_hp && (
                  <Chip icon={<SpeedIcon />} label={`${car.power_hp} KM`} size="small" variant="outlined" sx={{ '& .MuiChip-icon': { fontSize: 14 } }} />
                )}
                {!!car.transmission && (
                  <Chip icon={<SettingsIcon />}
                    label={(car.transmission as string) === 'Automatyczna' ? 'Automat' : car.transmission as string}
                    size="small"
                    color={(car.transmission as string) === 'Automatyczna' ? 'info' : 'default'}
                    variant={(car.transmission as string) === 'Automatyczna' ? 'filled' : 'outlined'}
                    sx={{ '& .MuiChip-icon': { fontSize: 14 } }} />
                )}
                {!!car.body_style && (
                  <Chip icon={<DirectionsCarIcon />} label={car.body_style as string} size="small" variant="outlined" sx={{ '& .MuiChip-icon': { fontSize: 14 } }} />
                )}
                {!!car.drive_type && (
                  <Chip label={(car.drive_type as string).replace(/^Napęd\s*/i, '')} size="small"
                    color={(car.drive_type as string).toLowerCase().includes('awd') || (car.drive_type as string).toLowerCase().includes('4x4') ? 'warning' : 'default'}
                    variant={(car.drive_type as string).toLowerCase().includes('awd') || (car.drive_type as string).toLowerCase().includes('4x4') ? 'filled' : 'outlined'}
                    sx={{ '& .MuiChip-icon': { fontSize: 14 } }} />
                )}
                {!!car.vehicle_class && (car.vehicle_class as string) !== 'Osobowy' && (
                  <Chip label={car.vehicle_class as string} size="small" variant="outlined" color="secondary" sx={{ '& .MuiChip-icon': { fontSize: 14 } }} />
                )}
              </Box>
            )}

            {!!(car.base_price_gross || car.total_price_gross) && (
              <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 0.5, flexWrap: 'wrap' }}>
                <Typography variant="caption" color="textSecondary" sx={{ fontSize: '0.7rem' }}>Katalog:</Typography>
                {car.base_price_gross && car.options_price_gross && car.total_price_gross ? (
                  <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
                    <strong>{cleanPrice(car.base_price_gross as string)}</strong>
                    {' + opcje '}
                    <strong>{cleanPrice(car.options_price_gross as string)}</strong>
                    {' = '}
                    <strong style={{ color: '#1565c0' }}>{cleanPrice(car.total_price_gross as string)} PLN brutto</strong>
                  </Typography>
                ) : car.total_price_gross ? (
                  <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600, color: '#1565c0' }}>
                    {cleanPrice(car.total_price_gross as string)} PLN brutto
                  </Typography>
                ) : (
                  <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600, color: '#1565c0' }}>
                    {cleanPrice(car.base_price_gross as string)} PLN brutto
                  </Typography>
                )}
              </Box>
            )}
          </Box>

          {/* Right Side: Score, Price, Cart Action */}
          <Box sx={{ textAlign: 'right', ml: 2, flexShrink: 0, minWidth: 170 }}>
            <Typography
              variant="h4"
              sx={{
                fontWeight: 'bold',
                color: (car.match_score_pct as number) === 100 ? 'success.main' :
                  (car.match_score_pct as number) >= 80 ? 'info.main' :
                    (car.match_score_pct as number) >= 50 ? 'warning.main' : 'error.main'
              }}
            >
              {car.match_score_pct as number}%
            </Typography>
            <Typography variant="caption" color="textSecondary">Dopasowanie</Typography>

            <LtrPriceBlock
              hasCache={!!(car.has_ltr_cache)}
              bestMonthlyPrice={(car.best_monthly_price as number) || null}
              marginPct={searchContext.margin_pct || 0}
              priceData={priceData}
              loading={pricesLoading}
            />

            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 0.5, mt: 0.75, flexWrap: 'wrap' }}>
              {!!car.has_ltr_cache && (
                <Button
                  size="small"
                  variant="contained"
                  color="secondary"
                  startIcon={<ShoppingCartIcon sx={{ fontSize: '14px !important' }} />}
                  sx={{ fontSize: '0.65rem', height: 24, textTransform: 'none', px: 1, minWidth: 0, boxShadow: 'none' }}
                  onClick={handleAddToCart}
                >
                  Dodaj do oferty
                </Button>
              )}
              {!!car.suggested_discount_pct && (car.suggested_discount_pct as number) > 0 && (
                <Tooltip title="Sugerowany rabat z bazy dealera">
                  <Chip icon={<LocalOfferIcon />}
                    label={`BD ${car.suggested_discount_pct}%`} size="small"
                    color="success" variant="filled"
                    sx={{ fontWeight: 700, '& .MuiChip-icon': { fontSize: 14 }, height: 24 }} />
                </Tooltip>
              )}
              {(!!car.service_cost_type || !!car.tire_class) && (
                <Tooltip title="Parametry użyte w kalkulacji">
                  <Chip icon={<BuildIcon />}
                    label={[
                      car.service_cost_type ? `Serwis: ${car.service_cost_type}` : null,
                      car.tire_class ? `Opony: ${car.tire_class}` : null
                    ].filter(Boolean).join(' | ')}
                    size="small" variant="outlined"
                    sx={{ fontSize: '0.65rem', '& .MuiChip-icon': { fontSize: 14 }, height: 24 }} />
                </Tooltip>
              )}
            </Box>
          </Box>
        </Box>

        {/* Feature Tags & Similars */}
        {matchedFeatures.length > 0 && (
          <Box sx={{ mt: 1.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 'bold' }}>Spełnione wymagania ({matchedFeatures.length}):</Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
              {matchedFeatures.map((f: string) => (
                <Chip key={f} label={f.replace(/_/g, ' ')} size="small" color="success" variant="outlined" />
              ))}
            </Box>
          </Box>
        )}

        {missingFeatures.length > 0 && (
          <Box sx={{ mt: 1.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 'bold' }}>Brakujące cechy ({missingFeatures.length}):</Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
              {missingFeatures.map((f: string) => (
                <Chip key={f} label={f.replace(/_/g, ' ')} size="small" color="error" variant="outlined" />
              ))}
            </Box>
          </Box>
        )}

        {similarData && similarData.length > 0 && (
          <SimilarVehiclesSection 
            vehicleId={vehicleId}
            similar={similarData}
            loading={similarLoading}
          />
        )}
      </CardContent>
    </Card>
  );
};

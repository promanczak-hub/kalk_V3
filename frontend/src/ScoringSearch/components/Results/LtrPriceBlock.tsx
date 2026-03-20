import React, { useState } from 'react';
import { Box, Typography, Chip, Tooltip, Skeleton, Button } from '@mui/material';
import type { PriceForParams } from '../../hooks/useBatchData';

interface LtrPriceBlockProps {
  hasCache: boolean;
  bestMonthlyPrice: number | null;
  marginPct?: number;
  priceData?: { price_for_params?: PriceForParams, variants?: PriceForParams[] };
  loading?: boolean;
}

export const LtrPriceBlock: React.FC<LtrPriceBlockProps> = ({
  hasCache, bestMonthlyPrice,
  marginPct = 0,
  priceData, loading = false
}) => {
  const price = priceData?.price_for_params;
  const variants = priceData?.variants;
  const [expanded, setExpanded] = useState(false);

  // Jeśli backend zwrócił found=true — pokaż cenę ZAWSZE (priorytet nad hasCache)
  const hasPriceFromAPI = price?.found === true && price?.monthly_price_net != null;

  // "Brak kalkulacji" tylko gdy: jest hasCache, dane załadowane, ale found=false i NIE ma ceny z API
  const isDataLoadedAndMissing = !loading && hasCache && !hasPriceFromAPI && !bestMonthlyPrice;

  // Gdy filtry Matrix nieaktywne priceData jest undefined — nie renderuj bloku w ogóle
  if (!priceData && !bestMonthlyPrice) return null;

  if (!hasPriceFromAPI && !bestMonthlyPrice) {
    return (
      <Box sx={{ mt: 0.75 }}>
        <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Typography variant="caption" color={isDataLoadedAndMissing ? 'error' : 'textSecondary'} sx={{ fontWeight: isDataLoadedAndMissing ? 'bold' : 'normal' }}>
            {isDataLoadedAndMissing ? 'Brak kalkulacji pasujących do tych parametrów' : 'Oczekuje na pierwszą kalkulację...'}
          </Typography>
        </Box>
      </Box>
    );
  }

  const rawPrice = price?.found && price.monthly_price_net != null
    ? price.monthly_price_net
    : bestMonthlyPrice;
  const m = Math.min(marginPct, 99) / 100.0;
  const displayPrice = rawPrice != null && m < 1.0 ? rawPrice / (1.0 - m) : null;

  const paramLabel = price?.found && price.duration_months != null && price.annual_mileage != null
    ? `${price.duration_months} mc / ${((price.annual_mileage * price.duration_months / 12) / 1000).toFixed(0)}k km`
    : null;

  return (
    <Box sx={{ mt: 0.75, textAlign: 'right', bgcolor: 'primary.main', color: 'primary.contrastText', px: 1.5, py: 1, borderRadius: 1 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="caption" sx={{ opacity: 0.9 }}>Rata LTR:</Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          {price?.variants_count != null && price.variants_count > 0 && (
             <Chip label={`Warianty zdefiniowane: ${price.variants_count}`} size="small" color="secondary" sx={{ height: 16, fontSize: '0.6rem' }} />
          )}
        </Box>
      </Box>
      {loading ? (
        <Skeleton variant="text" width={80} sx={{ ml: 'auto', bgcolor: 'rgba(255,255,255,0.2)' }} />
      ) : (
        <Typography variant="body1" sx={{ fontWeight: 'bold', mt: 0.5 }}>
          {Number(displayPrice).toLocaleString('pl-PL', { maximumFractionDigits: 0 })} PLN
        </Typography>
      )}
      {paramLabel && !loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
          <Tooltip title="Cena dla najlepszego dopasowania w historii kalkulacji">
            <Typography
              variant="caption"
              sx={{ opacity: 0.85, fontSize: '0.68rem', cursor: 'default' }}
            >
              {paramLabel}
            </Typography>
          </Tooltip>

          {price?.calculated_at && (
            <Box sx={{ display: 'flex', alignItems: 'center', ml: 0.5, borderLeft: '1px solid rgba(255,255,255,0.3)', pl: 0.5 }}>
              <Tooltip title={`Data ostatniej wykonanej na Vertex kalkulacji: ${new Date(price.calculated_at).toLocaleString('pl-PL')}`}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25, cursor: 'pointer', '&:hover': { opacity: 1 } }}>
                  <Typography variant="caption" sx={{ fontSize: '0.6rem', opacity: 0.7 }}>
                    {new Date(price.calculated_at).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit' })}
                  </Typography>
                </Box>
              </Tooltip>
            </Box>
          )}
        </Box>
      )}
      {!paramLabel && !loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
          <Typography variant="caption" sx={{ opacity: 0.9 }}>netto / mc</Typography>
        </Box>
      )}

      {variants && variants.length > 0 && (
        <Box sx={{ mt: 1, pt: 1, borderTop: '1px solid rgba(255,255,255,0.2)', display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          <Button 
            size="small" 
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }} 
            sx={{ fontSize: '0.65rem', textTransform: 'none', color: 'rgba(255,255,255,0.8)', py: 0, justifyContent: 'flex-end', '&:hover': { bgcolor: 'transparent', color: 'white' } }}
          >
            {expanded ? 'Pomiń warianty ▲' : `Inne warianty z historii (${variants.length}) ▼`}
          </Button>
          {expanded && variants.map((v, i) => {
            const variantPrice = v.monthly_price_net != null && m < 1.0 ? v.monthly_price_net / (1.0 - m) : 0;
            const uniqueKey = `kalk-${v.kalkulacja_id || i}`;
            const dateStr = v.calculated_at ? new Date(v.calculated_at).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit' }) : '';
            const paramsStr = [v.tire_class, v.service_type].filter(Boolean).join(' | ');
            
            return (
              <Typography key={uniqueKey} variant="caption" sx={{ fontSize: '0.65rem', display: 'flex', justifyContent: 'space-between', opacity: 0.85 }}>
                <span>{paramsStr} {dateStr ? `(${dateStr})` : ''}:</span>
                <span style={{ fontWeight: 600 }}>{Number(variantPrice).toLocaleString('pl-PL', { maximumFractionDigits: 0 })} PLN</span>
              </Typography>
            );
          })}
        </Box>
      )}
    </Box>
  );
};

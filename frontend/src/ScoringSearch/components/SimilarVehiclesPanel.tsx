import React from 'react';
import { Box, Typography, Card, CardContent, Chip, Tooltip, IconButton } from '@mui/material';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import AddIcon from '@mui/icons-material/Add';
import type { SimilarVehicle, SimilarityReasons } from '../hooks/useBatchData';
import { useOfferCartStore } from '../../stores/offerCartStore';

interface SimilarVehiclesPanelProps {
  vehicles: SimilarVehicle[];
  sourceVehicle: Record<string, unknown>;
}

// ── Similarity Category Logic ────────────────────────────────────────────────

interface SimilarityCategory {
  label: string;
  color: 'success' | 'primary' | 'info' | 'secondary' | 'warning' | 'default';
}

function getSimilarityCategory(v: SimilarVehicle): SimilarityCategory {
  const reasons = v.similarity_reasons;
  if (!reasons) return { label: 'Podobny wybór', color: 'default' };

  const { samar_match, body_match, fuel_match, price_pct_diff, equipment_match, is_same_brand } = reasons;
  const isCheap = price_pct_diff !== null && price_pct_diff >= 15;
  
  const targetFuel = (v.fuel || '').toLowerCase();
  const isEV = reasons.fuel_match === false && (
    targetFuel.includes('elektr') || 
    targetFuel.includes('ev') || 
    targetFuel.includes('bev') ||
    targetFuel.includes('plug-in')
  );

  // Hierarchy: most specific → least specific
  if (equipment_match && !is_same_brand) {
    return { label: 'Technologiczny Bliźniak', color: 'success' };
  }
  if (samar_match && body_match && price_pct_diff !== null && price_pct_diff <= 5) {
    return { label: 'Bliźniak', color: 'success' };
  }
  if (samar_match && body_match) {
    return { label: 'Ta sama klasa i typ', color: 'primary' };
  }
  if (samar_match && !body_match) {
    return { label: 'Ta sama klasa', color: 'primary' };
  }
  if (body_match && price_pct_diff !== null && price_pct_diff <= 10) {
    return { label: 'Ten sam typ', color: 'info' };
  }
  if (isCheap) {
    return { label: 'Znacznie tańszy', color: 'success' };
  }
  if (!fuel_match && isEV) {
    return { label: 'Alternatywa EV', color: 'secondary' };
  }
  if (body_match) {
    return { label: 'Ten sam typ nadwozia', color: 'info' };
  }

  return { label: 'Podobny wybór', color: 'default' };
}

// ── Reason Tags ───────────────────────────────────────────────────────────────

interface ReasonTag {
  icon: string;
  label: string;
}

function buildReasonTags(reasons: SimilarityReasons | null | undefined): ReasonTag[] {
  if (!reasons) return [];

  const tags: ReasonTag[] = [];

  if (reasons.equipment_match && reasons.equipment_similarity_pct) {
    tags.push({ icon: '✨', label: `Zbieżne opcje (${Math.round(reasons.equipment_similarity_pct)}%)` });
  }

  if (reasons.samar_match && reasons.samar_category && reasons.samar_category !== 'N/A') {
    tags.push({ icon: '🟢', label: `Klasa ${reasons.samar_category}` });
  }
  if (reasons.body_match && reasons.body_style && reasons.body_style !== 'N/A') {
    tags.push({ icon: '🟢', label: `Nadwozie: ${reasons.body_style}` });
  }
  if (reasons.price_pct_diff !== null && reasons.price_pct_diff <= 15) {
    const icon = reasons.price_pct_diff <= 5 ? '🟢' : '🟡';
    tags.push({ icon, label: `Cena ±${reasons.price_pct_diff}%` });
  }
  if (reasons.fuel_match) {
    tags.push({ icon: '🟢', label: 'Ten sam napęd' });
  }
  if (reasons.drive_match) {
    tags.push({ icon: '🟡', label: 'Ten sam typ 4x4/FWD' });
  }

  return tags.slice(0, 3); // Cap at 3 tags
}

// ── Tooltip Component ────────────────────────────────────────────────────────
const PriceOptionsTooltip: React.FC<{ reasons: SimilarityReasons | null | undefined }> = ({ reasons }) => {
  if (!reasons) return null;
  const options = reasons.paid_options || [];
  const basePrice = reasons.base_price;
  
  if (!basePrice && (!options || options.length === 0)) return null;

  return (
    <Box sx={{ p: 0.5, minWidth: 200 }}>
      {basePrice ? (
        <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1, borderBottom: '1px solid rgba(255,255,255,0.2)', pb: 0.5 }}>
          Cena bazowa: {basePrice.toLocaleString('pl-PL')} zł
        </Typography>
      ) : null}
      
      {options && options.length > 0 && (
        <>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)', display: 'block', mb: 0.5 }}>
            Opcje w tej konfiguracji:
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {options.map((opt: Record<string, unknown> | string, i: number) => {
              const name = typeof opt === 'string' ? opt : ((opt?.name as string) || (opt?.description as string) || 'Opcja');
              const price = typeof opt === 'object' && opt !== null && 'price_gross' in opt ? opt.price_gross 
                : (typeof opt === 'object' && opt !== null && 'price' in opt ? opt.price : null);
              
              return (
                <Box key={i} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
                  <Typography variant="caption" sx={{ fontSize: '0.65rem' }}>{name}</Typography>
                  {price !== null && (
                    <Typography variant="caption" sx={{ fontSize: '0.65rem', fontWeight: 'bold', whiteSpace: 'nowrap' }}>
                      {Number(price).toLocaleString('pl-PL')} zł
                    </Typography>
                  )}
                </Box>
              );
            })}
          </Box>
        </>
      )}
    </Box>
  );
};

// ── Component ──────────────────────────────────────────────────────────────────

export const SimilarVehiclesPanel: React.FC<SimilarVehiclesPanelProps> = ({ vehicles, sourceVehicle }) => {
  const addToCart = useOfferCartStore(state => state.addItem);

  const handleAddToCart = (e: React.MouseEvent, v: SimilarVehicle) => {
    e.stopPropagation();
    addToCart({
      id: crypto.randomUUID(),
      brand: v.brand || '',
      model: v.model || '',
      powertrain: v.fuel || '',
      vin_or_config: `Bliźniacza alternatywa dla: ${sourceVehicle.brand} ${sourceVehicle.model}`,
      term: 0,
      mileage: 0,
      net_installment: v.best_monthly_price || 0,
      contribution: 0,
      margin_pct: 0,
      calculation_data: v,
      standard_equipment: [],
      factory_options: [],
      dealer_options: [],
    });
  };

  if (!vehicles || vehicles.length === 0) {
    return null;
  }

  return (
    <Box sx={{ mt: 3, p: 2, bgcolor: 'rgba(0,0,0,0.015)', borderRadius: 2, border: '1px dashed', borderColor: 'divider' }}>
      <Typography
        variant="caption"
        sx={{
          mb: 1.5,
          color: 'text.secondary',
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: 0.5,
        }}
      >
        <DirectionsCarIcon sx={{ fontSize: 16 }} /> Inteligentne Alternatywy AI
      </Typography>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: 'repeat(1, 1fr)',
            sm: 'repeat(2, 1fr)',
            md: 'repeat(3, 1fr)',
            lg: 'repeat(5, 1fr)',
          },
          gap: 2,
        }}
      >
        {vehicles.map((v) => {
          const category = getSimilarityCategory(v);
          const tags = buildReasonTags(v.similarity_reasons);

          return (
            <Tooltip
              key={v.vehicle_id}
              title={<PriceOptionsTooltip reasons={v.similarity_reasons} />}
              placement="right"
              arrow
              disableInteractive
            >
              <Card
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  bgcolor: 'background.paper',
                  border: 1,
                  borderColor: 'divider',
                  boxShadow: 'none',
                  cursor: 'pointer',
                  borderRadius: 1.5,
                  transition: 'all 0.2s',
                  '&:hover': {
                    borderColor: 'primary.main',
                    transform: 'translateY(-2px)',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                  },
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  window.open(`/scoring-details/${v.vehicle_id}`, '_blank');
                }}
              >
              <CardContent sx={{ flexGrow: 1, p: 1.25, '&:last-child': { pb: 1.25 } }}>
                {/* Category chip */}
                <Box sx={{ mb: 0.75 }}>
                  <Tooltip
                    title={
                      tags.length > 0
                        ? tags.map((t) => `${t.icon} ${t.label}`).join('  •  ')
                        : 'Brak szczegółów podobieństwa'
                    }
                    placement="top"
                    arrow
                  >
                    <Chip
                      size="small"
                      label={category.label}
                      color={category.color}
                      sx={{ height: 18, fontSize: '0.6rem', fontWeight: 700, borderRadius: '4px', cursor: 'help' }}
                    />
                  </Tooltip>
                </Box>

                {/* Reason tags — always visible, max 3 */}
                {tags.length > 0 && (
                  <Box sx={{ mb: 0.5, display: 'flex', flexDirection: 'column', gap: 0.25 }}>
                    {tags.slice(0, 3).map((tag, i) => (
                      <Typography
                         key={i}
                        variant="caption"
                        sx={{ fontSize: '0.58rem', color: 'text.secondary', lineHeight: 1.3 }}
                      >
                        {tag.icon} {tag.label}
                      </Typography>
                    ))}
                  </Box>
                )}

                {/* Vehicle name */}
                <Typography
                  variant="caption"
                  fontWeight="bold"
                  sx={{ display: 'block', mb: 0.5, lineHeight: 1.2, height: 28, overflow: 'hidden' }}
                >
                  {v.brand} {v.model}
                </Typography>

                {/* Price + score + add to cart */}
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    mt: 'auto',
                    pt: 0.75,
                    borderTop: '1px solid',
                    borderColor: 'rgba(0,0,0,0.05)',
                  }}
                >
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                    {v.best_monthly_price
                      ? `${v.best_monthly_price.toLocaleString('pl-PL')} zł`
                      : 'Wycena...'}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {v.similarity_score_pct && (
                      <Tooltip title="Wynik dopasowania cech" placement="top">
                        <Typography
                          variant="caption"
                          sx={{ color: 'success.main', fontWeight: 800, fontSize: '0.65rem' }}
                        >
                          {v.similarity_score_pct}%
                        </Typography>
                      </Tooltip>
                    )}
                    <Tooltip title="Dodaj alternatywę do koszyka">
                      <IconButton
                        size="small"
                        onClick={(e) => handleAddToCart(e, v)}
                        sx={{
                          p: 0.25,
                          color: 'primary.main',
                          bgcolor: 'primary.50',
                          borderRadius: 1,
                          '&:hover': { bgcolor: 'primary.100' }
                        }}
                      >
                        <AddIcon sx={{ fontSize: '1rem' }} />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Box>
              </CardContent>
            </Card>
            </Tooltip>
          );
        })}
      </Box>
    </Box>
  );
};

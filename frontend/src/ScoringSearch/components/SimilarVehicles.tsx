import React, { useState } from 'react';
import {
  Box, Typography, CircularProgress, Card, CardContent, Divider, Tooltip, IconButton, Link
} from '@mui/material';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { apiFetch } from '../../lib/api';

interface SimilarVehicle {
  vehicle_id: string;
  brand: string;
  model: string;
  version: string;
  body_type: string;
  fuel_type: string;
  transmission: string;
  best_monthly_price: number | null;
  image_url: string | null;
  similarity_score_pct: number | null;
}

interface SimilarVehiclesProps {
  vehicleId: string;
}

export const SimilarVehicles: React.FC<SimilarVehiclesProps> = ({ vehicleId }) => {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [vehicles, setVehicles] = useState<SimilarVehicle[]>([]);
  const [loaded, setLoaded] = useState(false);

  const loadSimilar = async () => {
    if (loaded) return;
    setLoading(true);
    try {
      const res = await apiFetch(`/api/scoring-search/vehicle/${vehicleId}/similar?limit=3`);
      if (res.ok) {
        const data = await res.json();
        setVehicles(data || []);
      }
    } catch (err) {
      console.error('Failed to load similar vehicles', err);
    } finally {
      setLoading(false);
      setLoaded(true);
    }
  };

  const handleExpand = () => {
    const nextState = !expanded;
    setExpanded(nextState);
    if (nextState && !loaded) {
      loadSimilar();
    }
  };

  return (
    <Box sx={{ mt: 2, borderTop: '1px dashed #e0e0e0', pt: 1 }}>
      <Box
        sx={{ display: 'flex', alignItems: 'center', cursor: 'pointer', opacity: 0.8, '&:hover': { opacity: 1 } }}
        onClick={handleExpand}
      >
        <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', display: 'flex', alignItems: 'center' }}>
          <ExpandMoreIcon sx={{ fontSize: 16, mr: 0.5, transform: expanded ? 'rotate(180deg)' : 'none', transition: '0.2s' }} />
          Tańsze alternatywy
        </Typography>
      </Box>

      {expanded && (
        <Box sx={{ mt: 1.5, display: 'flex', gap: 2, overflowX: 'auto', pb: 1 }}>
          {loading ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 2 }}>
              <CircularProgress size={16} />
              <Typography variant="caption" color="textSecondary">Szukanie podobnych...</Typography>
            </Box>
          ) : vehicles.length === 0 ? (
            <Typography variant="caption" color="textSecondary" sx={{ p: 1 }}>Brak zbliżonych ofert w niższej cenie.</Typography>
          ) : (
            vehicles.map((v) => (
              <Card key={v.vehicle_id} variant="outlined" sx={{ minWidth: 200, maxWidth: 220, flexShrink: 0, borderRadius: 2 }}>
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                  {v.image_url ? (
                    <Box sx={{ height: 80, mb: 1, backgroundImage: `url(${v.image_url})`, backgroundSize: 'cover', backgroundPosition: 'center', borderRadius: 1 }} />
                  ) : (
                    <Box sx={{ height: 80, mb: 1, bgcolor: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 1 }}>
                      <Typography variant="caption" color="textSecondary">Brak zdjęcia</Typography>
                    </Box>
                  )}
                  <Typography variant="subtitle2" sx={{ lineHeight: 1.1, fontSize: '0.8rem', fontWeight: 700 }} noWrap>
                    {v.brand} {v.model}
                  </Typography>
                  <Tooltip title={v.version}>
                    <Typography variant="caption" color="textSecondary" display="block" noWrap sx={{ fontSize: '0.65rem' }}>
                      {v.version}
                    </Typography>
                  </Tooltip>
                  <Divider sx={{ my: 0.5 }} />
                  <Typography variant="caption" display="block" sx={{ fontSize: '0.65rem' }}>
                    {v.body_type} • {v.fuel_type} • {v.transmission === 'Automatyczna' ? 'Automat' : v.transmission}
                  </Typography>
                  {v.similarity_score_pct !== null && (
                     <Typography variant="caption" display="block" color="success.main" sx={{ fontSize: '0.65rem', fontWeight: 'bold' }}>
                       Zgodność opcji: {v.similarity_score_pct}%
                     </Typography>
                  )}
                  
                  <Box sx={{ mt: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2" color="primary" sx={{ fontWeight: 800 }}>
                      {v.best_monthly_price ? `${Number(v.best_monthly_price).toLocaleString('pl-PL')} PLN` : 'Brak kalk.'}
                    </Typography>
                    <IconButton size="small" component={Link} href={`#`} sx={{ p: 0 }}>
                      <KeyboardArrowRightIcon fontSize="small" />
                    </IconButton>
                  </Box>
                </CardContent>
              </Card>
            ))
          )}
        </Box>
      )}
    </Box>
  );
};

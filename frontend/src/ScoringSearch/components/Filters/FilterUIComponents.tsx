import React from 'react';
import { Box, Typography, Chip, FormGroup, FormControlLabel, Checkbox } from '@mui/material';
import type { OptionItem, SelectedFeature } from '../../types';

export const FilterChip: React.FC<{
  label: string;
  selected: boolean;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
  dim?: boolean;
}> = ({ label, selected, onClick, variant = 'primary', dim = false }) => {
  const selectedBg =
    variant === 'secondary'
      ? 'linear-gradient(135deg, #7c3aed 0%, #a78bfa 100%)'
      : 'linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)';

  return (
    <Chip
      label={label}
      size="small"
      onClick={onClick}
      sx={{
        cursor: dim ? 'not-allowed' : 'pointer',
        fontWeight: selected ? 700 : 400,
        fontSize: '0.75rem',
        height: 26,
        transition: 'all 0.15s ease',
        opacity: dim && !selected ? 0.35 : 1,
        background: selected ? selectedBg : '#f1f5f9',
        color: selected ? '#ffffff' : '#475569',
        border: selected ? 'none' : '1px solid #cbd5e1',
        boxShadow: selected ? '0 2px 6px rgba(59,130,246,0.35)' : 'none',
        pointerEvents: dim && !selected ? 'none' : undefined,
        '&:hover': {
          transform: dim ? 'none' : 'scale(1.04)',
          background: selected ? selectedBg : '#e2e8f0',
          boxShadow: selected
            ? '0 4px 10px rgba(59,130,246,0.45)'
            : '0 1px 4px rgba(0,0,0,0.08)',
        },
      }}
    />
  );
};

export const SectionBadge: React.FC<{ count: number }> = ({ count }) =>
  count > 0 ? (
    <Box
      sx={{
        ml: 'auto',
        bgcolor: '#3b82f6',
        color: 'white',
        borderRadius: 10,
        px: 0.8,
        py: 0.1,
        fontSize: '0.65rem',
        fontWeight: 700,
        lineHeight: 1.6,
        minWidth: 18,
        textAlign: 'center',
      }}
    >
      {count}
    </Box>
  ) : null;

export const SectionLabel: React.FC<{ label: string; selectedCount?: number }> = ({
  label,
  selectedCount = 0,
}) => (
  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
    <Typography
      variant="subtitle2"
      sx={{
        fontWeight: 700,
        color: '#64748b',
        fontSize: '0.75rem',
        textTransform: 'uppercase',
        letterSpacing: 1.0,
      }}
    >
      {label}
    </Typography>
    <SectionBadge count={selectedCount} />
  </Box>
);

export const Section: React.FC<{ children: React.ReactNode; alt?: boolean }> = ({
  children,
  alt = false,
}) => (
  <Box
    sx={{
      p: 2,
      borderBottom: '1px solid #e2e8f0',
      bgcolor: alt ? '#f8fafc' : '#ffffff',
    }}
  >
    {children}
  </Box>
);

export const OptionsChecklist: React.FC<{
  items: OptionItem[];
  prefix: string;
  selectedFeatures: SelectedFeature[];
  isSelected: (prefix: string, name: string) => boolean;
  onToggle: (prefix: string, name: string) => void;
}> = ({ items, prefix, isSelected, onToggle }) => {
  if (items.length === 0) {
    return (
      <Typography variant="caption" color="textSecondary" sx={{ display: 'block', py: 1 }}>
        Brak pasujących opcji
      </Typography>
    );
  }
  return (
    <FormGroup>
      {items.slice(0, 50).map(item => (
        <FormControlLabel
          key={item.name}
          control={
            <Checkbox
              size="small"
              checked={isSelected(prefix, item.name)}
              onChange={() => onToggle(prefix, item.name)}
              sx={{ color: '#94a3b8', '&.Mui-checked': { color: '#7c3aed' }, py: 0.3 }}
            />
          }
          label={
            <Typography variant="body2" sx={{ fontSize: '0.78rem', color: '#475569' }}>
              {item.name}
              <Box component="span" sx={{ color: '#94a3b8', ml: 0.5, fontSize: '0.72rem' }}>({item.count})</Box>
              {item.is_sub_feature && (
                <Box
                  component="span"
                  title={
                    item.parent_packages && item.parent_packages.length > 0
                      ? `Występuje w: ${item.parent_packages.join(', ')}`
                      : 'Występuje wyłącznie jako element pakietów'
                  }
                  sx={{
                    ml: 0.7,
                    px: 0.6,
                    py: 0.1,
                    fontSize: '0.62rem',
                    fontWeight: 700,
                    color: '#7c3aed',
                    bgcolor: '#ede9fe',
                    border: '1px solid #c4b5fd',
                    borderRadius: 1,
                    verticalAlign: 'middle',
                    cursor: 'help',
                  }}
                >
                  📦 W PAKIECIE
                </Box>
              )}
            </Typography>
          }
          sx={{ m: 0, alignItems: 'flex-start' }}
        />
      ))}
      {items.length > 50 && (
        <Typography variant="caption" color="textSecondary" sx={{ mt: 0.5 }}>
          Pokazano 50 z {items.length} — zawęź wyszukiwanie
        </Typography>
      )}
    </FormGroup>
  );
};

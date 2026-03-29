import React, { useState, useEffect } from 'react';
import { Box, TextField, InputAdornment, IconButton, Tooltip } from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import ClearIcon from '@mui/icons-material/Clear';
import type { SearchContext } from '../types';

interface OmniboxSearchProps {
  searchContext: SearchContext;
  onContextChange: (ctx: SearchContext) => void;
}

export const OmniboxSearch: React.FC<OmniboxSearchProps> = ({ searchContext, onContextChange }) => {
  const [localQuery, setLocalQuery] = useState(searchContext.semanticQuery || '');
  const isTyping = React.useRef(false);

  useEffect(() => {
    if (!searchContext.semanticQuery && !isTyping.current) {
      // Intentionally syncing local state directly in effect to clear on external clear
      setLocalQuery('');
    }
  }, [searchContext.semanticQuery]);

  useEffect(() => {
    const handler = setTimeout(() => {
       if (searchContext.semanticQuery !== localQuery) {
          onContextChange({ ...searchContext, semanticQuery: localQuery });
          isTyping.current = false;
       }
    }, 600); // 600ms debounce

    return () => clearTimeout(handler);
  }, [localQuery, searchContext, onContextChange]);

  const handleClear = () => {
    setLocalQuery('');
    onContextChange({ ...searchContext, semanticQuery: '' });
  };

  return (
    <Box sx={{ p: 2, pb: 0 }}>
      <TextField
        fullWidth
        variant="outlined"
        placeholder="Opisz auto (np. 'czerwony SUV premium z dużą mocą...')"
        value={localQuery}
        onChange={(e) => setLocalQuery(e.target.value)}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Tooltip title="Wyszukiwanie Wspierane Przez AI (Gemini)">
                <AutoAwesomeIcon sx={{ color: 'primary.main' }} />
              </Tooltip>
            </InputAdornment>
          ),
          endAdornment: localQuery ? (
            <InputAdornment position="end">
              <IconButton size="small" onClick={handleClear}>
                <ClearIcon fontSize="small" />
              </IconButton>
            </InputAdornment>
          ) : null,
          sx: {
            borderRadius: 2,
            bgcolor: 'background.paper',
            '&.Mui-focused': {
              boxShadow: '0 0 0 2px rgba(59, 130, 246, 0.5)',
            }
          }
        }}
      />
    </Box>
  );
};

import React from 'react';
import {
  Box, Paper, Typography, Divider, CircularProgress,
  Snackbar, Alert
} from '@mui/material';
import { OmniboxSearch } from './components/OmniboxSearch';
import { ScoringFilters } from './components/ScoringFilters';
import { ScoringResults } from './components/ScoringResults';
import { useScoringSearch } from './hooks/useScoringSearch';

export const ScoringSearchPage: React.FC = () => {
  const {
    searchContext,
    setSearchContext,
    selectedFeatures,
    setSelectedFeatures,
    searchResults,
    isSearching,
    snackbarMessage,
    setSnackbarMessage
  } = useScoringSearch();

  return (
    <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3, height: { md: 'calc(100vh - 120px)' } }}>
      {/* Left Column - Filters */}
      <Box sx={{ width: { xs: '100%', md: 320 }, flexShrink: 0, height: { xs: 'auto', md: '100%' } }}>
        <Paper elevation={2} sx={{ p: 0, height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ p: 2, background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)', color: 'primary.contrastText', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="h6">Wyszukiwarka Ofert</Typography>
              <Typography variant="body2" sx={{ opacity: 0.8 }}>Zbuduj profil Idealnego Auta</Typography>
            </Box>
          </Box>
          <Divider />
          <OmniboxSearch
            searchContext={searchContext}
            onContextChange={setSearchContext}
          />
          <Box sx={{ p: 0, flexGrow: 1, overflowY: 'auto' }}>
            <ScoringFilters 
              searchContext={searchContext}
              onContextChange={setSearchContext}
              selectedFeatures={selectedFeatures}
              onFeaturesChange={setSelectedFeatures}
            />
          </Box>
        </Paper>
      </Box>

      {/* Right Column - Results */}
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Paper elevation={2} sx={{ p: 0, height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="h6">Wyniki Dopasowania ({searchResults.length})</Typography>
              {isSearching && <CircularProgress size={24} />}
            </Box>
          </Box>

          <Box sx={{ p: 2, flexGrow: 1, overflowY: 'auto', bgcolor: 'background.default' }}>
            <ScoringResults 
              results={searchResults} 
              loading={isSearching} 
              searchContext={searchContext}
              selectedFeatures={selectedFeatures}
            />
          </Box>
        </Paper>
      </Box>

      <Snackbar open={!!snackbarMessage} autoHideDuration={6000} onClose={() => setSnackbarMessage(null)}>
        <Alert onClose={() => setSnackbarMessage(null)} severity="info" sx={{ width: '100%' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

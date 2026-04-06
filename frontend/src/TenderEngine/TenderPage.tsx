import React, { useEffect, useCallback, useRef } from 'react';
import {
  Box, Paper, Typography, Divider, Alert, Button, Tooltip,
} from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import GavelIcon from '@mui/icons-material/Gavel';
import { TenderCriteriaBuilder } from './components/TenderCriteriaBuilder';
import { TenderResultsView } from './components/TenderResultsView';
import { useTenderEngine } from './hooks/useTenderEngine';

export const TenderPage: React.FC = () => {
  const {
    dictionary,
    criteria,
    results,
    isLoading,
    isLoadingDict,
    error,
    fetchDictionary,
    addCriterion,
    updateCriterion,
    removeCriterion,
    clearCriteria,
    evaluate,
    uploadFile,
    setError,
  } = useTenderEngine();

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchDictionary();
  }, [fetchDictionary]);

  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      uploadFile(file);
    }
    // Reset input so the same file can be re-uploaded
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [uploadFile]);

  return (
    <Box sx={{
      display: 'flex',
      flexDirection: { xs: 'column', md: 'row' },
      gap: 3,
      height: { md: 'calc(100vh - 120px)' },
    }}>
      {/* Left Column — Criteria Builder */}
      <Box sx={{ width: { xs: '100%', md: 380 }, flexShrink: 0, height: { xs: 'auto', md: '100%' } }}>
        <Paper elevation={2} sx={{ p: 0, height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {/* Header */}
          <Box sx={{
            p: 2,
            background: 'linear-gradient(135deg, #7c3aed 0%, #a855f7 100%)',
            color: 'white',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <GavelIcon sx={{ fontSize: 22 }} />
              <Box>
                <Typography variant="h6" sx={{ lineHeight: 1.2 }}>Tender Engine</Typography>
                <Typography variant="caption" sx={{ opacity: 0.8 }}>
                  Ocena zgodności pojazdów z wymaganiami przetargu
                </Typography>
              </Box>
            </Box>
          </Box>

          <Divider />

          {/* Upload button */}
          <Box sx={{ px: 2, pt: 2, display: 'flex', gap: 1 }}>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
              id="tender-file-upload"
            />
            <Tooltip title="Importuj kryteria z pliku Excel lub CSV">
              <Button
                variant="outlined"
                size="small"
                startIcon={<UploadFileIcon />}
                onClick={() => fileInputRef.current?.click()}
                sx={{ textTransform: 'none', fontSize: '0.8rem' }}
                fullWidth
              >
                Importuj z Excel / CSV
              </Button>
            </Tooltip>
          </Box>

          {/* Error */}
          {error && (
            <Box sx={{ px: 2, pt: 1 }}>
              <Alert
                severity="error"
                onClose={() => setError(null)}
                sx={{ fontSize: '0.78rem' }}
              >
                {error}
              </Alert>
            </Box>
          )}

          {/* Criteria builder */}
          <Box sx={{ p: 2, flexGrow: 1, overflowY: 'auto' }}>
            <TenderCriteriaBuilder
              dictionary={dictionary}
              criteria={criteria}
              isLoadingDict={isLoadingDict}
              onAdd={addCriterion}
              onUpdate={updateCriterion}
              onRemove={removeCriterion}
              onClear={clearCriteria}
              onEvaluate={evaluate}
              isEvaluating={isLoading}
            />
          </Box>
        </Paper>
      </Box>

      {/* Right Column — Results */}
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Paper elevation={2} sx={{ p: 0, height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Results header */}
          <Box sx={{
            p: 2,
            borderBottom: 1,
            borderColor: 'divider',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="h6">
                Wyniki Oceny Przetargowej
                {results && (
                  <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                    ({results.total_vehicles} pojazdów)
                  </Typography>
                )}
              </Typography>
            </Box>
          </Box>

          {/* Results content */}
          <Box sx={{ p: 2, flexGrow: 1, overflowY: 'auto', bgcolor: 'background.default' }}>
            <TenderResultsView results={results} isLoading={isLoading} />
          </Box>
        </Paper>
      </Box>
    </Box>
  );
};

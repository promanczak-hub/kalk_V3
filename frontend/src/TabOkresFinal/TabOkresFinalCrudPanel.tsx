import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
  Typography,
  Chip,
  Button,
  TextField,
  InputAdornment,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import RefreshIcon from '@mui/icons-material/Refresh';
import SearchIcon from '@mui/icons-material/Search';
import { apiClient } from '../lib/apiClient';
import { API_BASE_URL } from '../config/env';

interface TabOkresFinalRow {
  id: string;
  samar_class: string;
  engine_type: string;
  year_0: number;
  year_1: number;
  year_2: number;
  year_3: number;
  year_4: number;
  year_5: number;
  year_6: number;
  year_7: number;
}

export default function TabOkresFinalCrudPanel() {
  const [rows, setRows] = useState<TabOkresFinalRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [changedRows, setChangedRows] = useState<Record<string, Partial<TabOkresFinalRow>>>({});

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.fetch(`${API_BASE_URL}/api/tab-okres-final`);
      if (!res.ok) throw new Error('Failed to fetch data');
      const data = await res.json();
      setRows(data);
      setChangedRows({});
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCellChange = (id: string, field: keyof TabOkresFinalRow, value: string) => {
    const numValue = parseFloat(value.replace(',', '.'));
    if (isNaN(numValue) && value !== '') return;

    setChangedRows(prev => ({
      ...prev,
      [id]: {
        ...(prev[id] || {}),
        [field]: value === '' ? 0 : numValue
      }
    }));
  };

  const handleSaveRow = async (id: string) => {
    const updates = changedRows[id];
    if (!updates) return;

    setSavingId(id);
    try {
      const originalRow = rows.find(r => r.id === id);
      if (!originalRow) return;

      const payload = { ...originalRow, ...updates };
      const res = await apiClient.fetch(`${API_BASE_URL}/api/tab-okres-final/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error('Failed to save data');
      
      const updatedRow = await res.json();
      setRows(prev => prev.map(r => r.id === id ? updatedRow : r));
      setChangedRows(prev => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingId(null);
    }
  };

  const filteredRows = rows.filter(row => 
    row.samar_class.toLowerCase().includes(searchTerm.toLowerCase()) ||
    row.engine_type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const years = [0, 1, 2, 3, 4, 5, 6, 7];

  return (
    <Box sx={{ mt: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>📊 TAB. OKRES FINAL (CRUD)</Typography>
          <Typography variant="body2" color="text.secondary">Zarządzanie współczynnikami okresu finalnego według klas i napędów.</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            size="small"
            placeholder="Szukaj klasy/napędu..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            }}
          />
          <Button startIcon={<RefreshIcon />} onClick={fetchData} disabled={loading}>Odśwież</Button>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <TableContainer component={Paper} sx={{ maxHeight: '75vh', border: '1px solid', borderColor: 'divider' }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 800, bgcolor: 'grey.50', minWidth: 200 }}>Klasa</TableCell>
              <TableCell sx={{ fontWeight: 800, bgcolor: 'grey.50', minWidth: 150 }}>Napęd</TableCell>
              {years.map(y => (
                <TableCell key={y} align="center" sx={{ fontWeight: 800, bgcolor: 'grey.50', minWidth: 80 }}>Rok {y}</TableCell>
              ))}
              <TableCell align="center" sx={{ fontWeight: 800, bgcolor: 'grey.50', minWidth: 100 }}>Akcje</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={11} align="center" sx={{ py: 10 }}><CircularProgress /></TableCell></TableRow>
            ) : filteredRows.length === 0 ? (
              <TableRow><TableCell colSpan={11} align="center" sx={{ py: 5 }}>Brak danych.</TableCell></TableRow>
            ) : (
              filteredRows.map((row) => (
                <TableRow key={row.id} hover>
                  <TableCell sx={{ fontSize: '0.8rem', fontWeight: 600 }}>{row.samar_class}</TableCell>
                  <TableCell>
                    <Chip label={row.engine_type} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                  </TableCell>
                  {years.map(y => {
                    const field = `year_${y}` as keyof TabOkresFinalRow;
                    const changeSet = changedRows[row.id];
                    const isChanged = changeSet && field in changeSet;
                    const value = isChanged ? changeSet[field] : row[field];
                    
                    return (
                      <TableCell key={y} align="center" sx={{ p: '2px' }}>
                        <TextField
                          type="number"
                          size="small"
                          value={value}
                          onChange={(e) => handleCellChange(row.id, field, e.target.value)}
                          inputProps={{ step: '0.01', style: { textAlign: 'center', fontSize: '0.8rem', padding: '4px' } }}
                          sx={{ 
                            width: 65,
                            '& .MuiOutlinedInput-root': {
                              bgcolor: isChanged ? 'warning.light' : 'transparent',
                              '& fieldset': {
                                border: isChanged ? '1px solid orange' : '1px solid transparent',
                              },
                              '&:hover fieldset': {
                                border: '1px solid lightgrey',
                              },
                              '&.Mui-focused fieldset': {
                                border: '2px solid #1976d2',
                              }
                            }
                          }}
                        />
                      </TableCell>
                    );
                  })}
                  <TableCell align="center">
                    <Button
                      variant="contained"
                      size="small"
                      color="primary"
                      startIcon={savingId === row.id ? <CircularProgress size={14} color="inherit" /> : <SaveIcon fontSize="small" />}
                      disabled={!changedRows[row.id] || savingId === row.id}
                      onClick={() => handleSaveRow(row.id)}
                      sx={{ fontSize: '0.7rem', py: 0.5 }}
                    >
                      Save
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

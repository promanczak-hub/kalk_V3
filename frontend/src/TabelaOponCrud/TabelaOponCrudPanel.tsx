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
  Button,
  TextField,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Alert,
  Typography
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import { supabase } from '../VertexExtractor/lib/supabaseClient';

interface TireCostRow {
  srednica: number;
  budget: number;
  medium: number;
  premium: number;
  wzmocnione_budget: number;
  wzmocnione_medium: number;
  wzmocnione_premium: number;
  wielosezon_budget: number;
  wielosezon_medium: number;
  wielosezon_premium: number;
  wielosezon_wzmocnione_budget: number;
  wielosezon_wzmocnione_medium: number;
  wielosezon_wzmocnione_premium: number;
}

export default function TabelaOponCrudPanel() {
  const [rows, setRows] = useState<TireCostRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Dialog state
  const [openDialog, setOpenDialog] = useState(false);
  const [editRow, setEditRow] = useState<TireCostRow | null>(null);
  const [formData, setFormData] = useState<Partial<TireCostRow>>({});

  const columns = [
    { name: 'budget', label: 'Budget' },
    { name: 'medium', label: 'Medium' },
    { name: 'premium', label: 'Premium' },
    { name: 'wzmocnione_budget', label: 'Wzmocnione Budget' },
    { name: 'wzmocnione_medium', label: 'Wzmocnione Medium' },
    { name: 'wzmocnione_premium', label: 'Wzmocnione Premium' },
    { name: 'wielosezon_budget', label: 'Wielosezonowe Budget' },
    { name: 'wielosezon_medium', label: 'Wielosezonowe Medium' },
    { name: 'wielosezon_premium', label: 'Wielosezonowe Premium' },
    { name: 'wielosezon_wzmocnione_budget', label: 'Wielosez.+Wzmocnione Budget' },
    { name: 'wielosezon_wzmocnione_medium', label: 'Wielosez.+Wzmocnione Medium' },
    { name: 'wielosezon_wzmocnione_premium', label: 'Wielosez.+Wzmocnione Premium' }
  ];

  const fetchData = useCallback(async () => {
    setLoading(true);
    const { data, error } = await supabase.from('koszty_opon').select('*').order('srednica', { ascending: true });
    if (error) {
      setError(error.message);
    } else {
      setRows(data || []);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleOpenEdit = (row: TireCostRow) => {
    setEditRow(row);
    setFormData({ ...row });
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
  };

  const handleSave = async () => {
    setLoading(true);
    if (editRow) {
      const { error } = await supabase
        .from('koszty_opon')
        .update(formData)
        .eq('srednica', editRow.srednica);
      if (error) {
        setError(error.message);
      } else {
        fetchData();
      }
    }
    setOpenDialog(false);
    setLoading(false);
  };

  return (
    <Box sx={{ mt: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h6">Tabela Kosztów Opon (PLN)</Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <TableContainer component={Paper} sx={{ maxHeight: 650 }}>
        {loading ? (
          <Box display="flex" justifyContent="center" p={5}><CircularProgress /></Box>
        ) : (
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 'bold', whiteSpace: 'nowrap' }}>Akcje</TableCell>
                <TableCell sx={{ fontWeight: 'bold', whiteSpace: 'nowrap' }}>Średnica</TableCell>
                {columns.map(col => (
                  <TableCell key={col.name} sx={{ fontWeight: 'bold' }}>{col.label}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.srednica} hover>
                  <TableCell>
                    <IconButton size="small" color="primary" onClick={() => handleOpenEdit(row)}>
                      <EditIcon fontSize="small"/>
                    </IconButton>
                  </TableCell>
                  <TableCell sx={{ fontSize: '1.1em', fontWeight: 500 }}>{row.srednica}"</TableCell>
                  {columns.map(col => (
                    <TableCell key={col.name}>{String(row[col.name as keyof TireCostRow] ?? '0')} zł</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>Edycja Kosztów dla średnicy {editRow?.srednica}"</DialogTitle>
        <DialogContent dividers>
          <Box display="grid" gridTemplateColumns="repeat(3, 1fr)" gap={2} pt={1}>
            {columns.map(col => (
              <TextField
                key={col.name}
                label={col.label}
                type="number"
                value={formData[col.name as keyof TireCostRow] ?? ''}
                onChange={(e) => {
                  const val = e.target.value;
                  setFormData({
                    ...formData,
                    [col.name]: val === '' ? null : Number(val)
                  });
                }}
                fullWidth
                variant="outlined"
                size="small"
              />
            ))}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Anuluj</Button>
          <Button variant="contained" onClick={handleSave} disabled={loading}>
            Zapisz
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

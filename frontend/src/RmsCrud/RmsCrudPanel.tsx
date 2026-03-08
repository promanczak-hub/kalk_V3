import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
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
  Alert
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import { RMSTablesSchema } from './rms_schema';
import { supabase } from '../VertexExtractor/lib/supabaseClient';
import ConfigTableToolbar from '../components/ConfigTableToolbar';

export default function RmsCrudPanel() {
  const tableNames = Object.keys(RMSTablesSchema);
  const [selectedTable, setSelectedTable] = useState<string>(tableNames[0]);
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Dialog state
  const [openDialog, setOpenDialog] = useState(false);
  const [editRow, setEditRow] = useState<any>(null); // null means adding a new row
  const [formData, setFormData] = useState<any>({});

  const columns = (RMSTablesSchema as any)[selectedTable] || [];

  const fetchData = useCallback(async () => {
    setLoading(true);
    const { data, error } = await supabase.from(selectedTable).select('*');
    if (error) {
      setError(error.message);
    } else {
      setRows(data || []);
    }
    setLoading(false);
  }, [selectedTable]);

  useEffect(() => {
    if (selectedTable) {
      fetchData();
    }
  }, [selectedTable, fetchData]);

  const handleOpenEdit = (row: any) => {
    setEditRow(row);
    setFormData({ ...row });
    setOpenDialog(true);
  };

  const handleOpenAdd = () => {
    setEditRow(null);
    setFormData({});
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
  };

  const handleSave = async () => {
    setLoading(true);
    // Pandas generated tables don't have PKs, so we use full row matching for updates
    if (!editRow) {
      // INSERT
      const { error } = await supabase.from(selectedTable).insert([formData]);
      if (error) setError(error.message);
      else fetchData();
    } else {
      // UPDATE - Match strictly on old data
      let query = supabase.from(selectedTable).update(formData);
      for (const col of Object.keys(editRow)) {
        if (editRow[col] === null) {
          query = query.is(col, null);
        } else {
          query = query.eq(col, editRow[col]);
        }
      }
      
      const { error } = await query;
      if (error) setError(error.message);
      else fetchData();
    }
    setOpenDialog(false);
    setLoading(false);
  };

  const handleDelete = async (row: any) => {
    setLoading(true);
    let query = supabase.from(selectedTable).delete();
    for (const col of Object.keys(row)) {
      if (row[col] === null) {
        query = query.is(col, null);
      } else {
        query = query.eq(col, row[col]);
      }
    }
    const { error } = await query;
    if (error) setError(error.message);
    else fetchData();
    setLoading(false);
  };

  return (
    <Box sx={{ mt: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <FormControl sx={{ minWidth: 350 }}>
          <InputLabel>Tabela Bazy (RMS _czak)</InputLabel>
          <Select
            value={selectedTable}
            label="Tabela Bazy (RMS _czak)"
            onChange={(e) => setSelectedTable(e.target.value)}
          >
            {tableNames.map(name => (
              <MenuItem key={name} value={name}>{name}</MenuItem>
            ))}
          </Select>
        </FormControl>
        
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <ConfigTableToolbar tableName={selectedTable} tableLabel={selectedTable} onDataChanged={fetchData} />
          <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={handleOpenAdd}>
            Dodaj Rekord
          </Button>
        </Box>
      </Box>
      
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <TableContainer component={Paper} sx={{ maxHeight: 650 }}>
        {loading ? (
          <Box display="flex" justifyContent="center" p={5}><CircularProgress /></Box>
        ) : (
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell width={100} sx={{ fontWeight: 'bold' }}>Akcje</TableCell>
                {columns.map((col: any) => (
                  <TableCell key={col.name} sx={{ fontWeight: 'bold' }}>{col.name}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row, idx) => (
                <TableRow key={idx} hover>
                  <TableCell>
                    <IconButton size="small" color="primary" onClick={() => handleOpenEdit(row)}>
                      <EditIcon fontSize="small"/>
                    </IconButton>
                    <IconButton size="small" color="error" onClick={() => handleDelete(row)}>
                      <DeleteIcon fontSize="small"/>
                    </IconButton>
                  </TableCell>
                  {columns.map((col: any) => (
                    <TableCell key={col.name}>{String(row[col.name] ?? '')}</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>{editRow ? "Edytuj Rekord" : "Dodaj Rekord"}</DialogTitle>
        <DialogContent dividers>
          <Box display="flex" flexDirection="column" gap={3} pt={1}>
            {columns.map((col: any) => (
              <TextField 
                key={col.name}
                label={col.name + ` (${col.type})`} 
                value={formData[col.name] !== undefined && formData[col.name] !== null ? formData[col.name] : ''}
                onChange={(e) => {
                  const val = e.target.value;
                  const newFormData = { ...formData };
                  if (col.type === 'number') {
                    newFormData[col.name] = val === '' ? null : Number(val);
                  } else if (col.type === 'boolean') {
                    newFormData[col.name] = val === 'true' ? true : val === 'false' ? false : null;
                  } else {
                    newFormData[col.name] = val;
                  }
                  setFormData(newFormData);
                }}
                fullWidth 
                variant="outlined"
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

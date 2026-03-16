import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  IconButton,
  CircularProgress,
  Alert
} from "@mui/material";
import { Edit, Trash2, Plus } from "lucide-react";
import { supabase } from "../VertexExtractor/lib/supabaseClient";

interface TransportFee {
  id: string;
  brand: string;
  fee_net: number;
}

export default function TransportFeesPanel() {
  const [data, setData] = useState<TransportFee[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [modalOpen, setModalOpen] = useState(false);
  const [formData, setFormData] = useState<Partial<TransportFee>>({
    brand: "",
    fee_net: 0.0,
  });
  const [editingId, setEditingId] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    const { data: resp, error: err } = await supabase.from("transport_fees").select("*").order("brand");
    if (err) {
      setError(err.message);
    } else {
      setData(resp as TransportFee[]);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleOpen = (item?: TransportFee) => {
    if (item) {
      setFormData({ brand: item.brand, fee_net: item.fee_net });
      setEditingId(item.id);
    } else {
      setFormData({ brand: "", fee_net: 0.0 });
      setEditingId(null);
    }
    setModalOpen(true);
  };

  const handleClose = () => setModalOpen(false);

  const handleSave = async () => {
    try {
      if (editingId) {
        const { error } = await supabase
          .from("transport_fees")
          .update({ brand: formData.brand, fee_net: formData.fee_net })
          .eq("id", editingId);
        if (error) throw error;
      } else {
        const { error } = await supabase
          .from("transport_fees")
          .insert({ brand: formData.brand, fee_net: formData.fee_net });
        if (error) throw error;
      }
      fetchData();
      handleClose();
    } catch (e) {
      console.error(e);
      alert("Błąd zapisu: " + (e as Error).message);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Na pewno usunąć opłatę dla tej marki?")) return;
    try {
      const { error } = await supabase.from("transport_fees").delete().eq("id", id);
      if (error) throw error;
      fetchData();
    } catch (e) {
      console.error(e);
      alert("Błąd przy usuwaniu: " + (e as Error).message);
    }
  };

  return (
    <Box sx={{ mt: 2 }}>
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2, alignItems: 'center' }}>
        <Typography variant="h6">Tabela Opłat Transportowych (PLN Netto)</Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<Plus size={16} />}
            onClick={() => handleOpen()}
            sx={{ textTransform: "none" }}
          >
            Dodaj Opłatę
          </Button>
        </Box>
      </Box>

      {loading ? (
        <CircularProgress />
      ) : (
        <TableContainer component={Paper} sx={{ maxHeight: 650 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 'bold' }}>Marka (Brand)</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Opłata Transportowa Netto</TableCell>
                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Akcje</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.map((row) => (
                <TableRow key={row.id} hover>
                  <TableCell sx={{ fontWeight: 500 }}>{row.brand}</TableCell>
                  <TableCell>{Number(row.fee_net).toFixed(2)} zł</TableCell>
                  <TableCell align="right">
                    <IconButton size="small" onClick={() => handleOpen(row)} color="primary">
                      <Edit size={16} />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleDelete(row.id)}
                    >
                      <Trash2 size={16} />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {data.length === 0 && (
                <TableRow>
                  <TableCell colSpan={3} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                    Brak zdefiniowanych opłat transportowych. Zostanie użyte 0 PLN tam gdzie brakuje.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={modalOpen} onClose={handleClose} fullWidth maxWidth="sm">
        <DialogTitle>{editingId ? "Edytuj Opłatę Transportową" : "Nowa Opłata Transportowa"}</DialogTitle>
        <DialogContent dividers sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <TextField
            label="Marka (np. Skoda)"
            size="small"
            value={formData.brand || ""}
            onChange={(e) => setFormData({ ...formData, brand: e.target.value })}
            autoFocus
          />
          <TextField
            label="Opłata Netto (PLN)"
            type="number"
            size="small"
            value={formData.fee_net || 0}
            onChange={(e) => setFormData({ ...formData, fee_net: parseFloat(e.target.value) || 0.0 })}
            inputProps={{ step: "0.01", min: "0" }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Anuluj</Button>
          <Button variant="contained" onClick={handleSave} disabled={!formData.brand}>
            Zapisz
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

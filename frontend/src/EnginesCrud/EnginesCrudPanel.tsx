import { useState, useEffect } from "react";
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
  MenuItem,
  IconButton,
  CircularProgress,
  Chip,
} from "@mui/material";
import { Edit, Trash2, Plus } from "lucide-react";
import ConfigTableToolbar from '../components/ConfigTableToolbar';

interface EngineType {
  id?: number;
  name: string;
  category: string;
  description?: string;
}

const CATEGORIES = [
  "Konwencjonalne (ICE)",
  "Miękkie Hybrydy (mHEV)",
  "Napędy Alternatywne (Zelektryfikowane)",
];

const getCategoryColor = (category: string) => {
  switch (category) {
    case "Konwencjonalne (ICE)":
      return "default";
    case "Miękkie Hybrydy (mHEV)":
      return "primary";
    case "Napędy Alternatywne (Zelektryfikowane)":
      return "success";
    default:
      return "default";
  }
};

export default function EnginesCrudPanel() {
  const [data, setData] = useState<EngineType[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [formData, setFormData] = useState<EngineType>({
    name: "",
    category: CATEGORIES[0],
    description: "",
  });
  const [editingId, setEditingId] = useState<number | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`http://127.0.0.1:8000/api/engines`);
      if (resp.ok) {
        const json = await resp.json();
        setData(json);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleOpen = (item?: EngineType) => {
    if (item) {
      setFormData(item);
      setEditingId(item.id || null);
    } else {
      setFormData({
        name: "",
        category: CATEGORIES[0],
        description: "",
      });
      setEditingId(null);
    }
    setModalOpen(true);
  };

  const handleClose = () => setModalOpen(false);

  const handleSave = async () => {
    try {
      const resp = await fetch(`http://127.0.0.1:8000/api/engines`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      if (resp.ok) {
        fetchData();
        handleClose();
      } else {
        alert("Błąd zapisu");
      }
    } catch (e) {
      console.error(e);
      alert("Błąd komunikacji");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Na pewno usunąć?")) return;
    try {
      const resp = await fetch(`http://127.0.0.1:8000/api/engines/${id}`, {
        method: "DELETE",
      });
      if (resp.ok) {
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2, alignItems: 'center' }}>
        <Typography variant="h6">Słownik Napędów (Samar)</Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <ConfigTableToolbar tableName="engines" tableLabel="Napędy (Engines)" onDataChanged={fetchData} />
          <Button
            variant="contained"
            startIcon={<Plus size={16} />}
            onClick={() => handleOpen()}
          >
            Dodaj Napęd
          </Button>
        </Box>
      </Box>

      {loading ? (
        <CircularProgress />
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead sx={{ backgroundColor: "#f8fafc" }}>
              <TableRow>
                <TableCell>Nazwa Napędu</TableCell>
                <TableCell>Kategoria</TableCell>
                <TableCell>Opis</TableCell>
                <TableCell align="right">Akcje</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.map((row) => (
                <TableRow key={row.id}>
                  <TableCell sx={{ fontWeight: 500 }}>{row.name}</TableCell>
                  <TableCell>
                    <Chip 
                        label={row.category} 
                        size="small" 
                        color={getCategoryColor(row.category) as "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning"} 
                        variant="outlined"
                    />
                  </TableCell>
                  <TableCell>{row.description || "-"}</TableCell>
                  <TableCell align="right">
                    <IconButton size="small" onClick={() => handleOpen(row)} color="primary">
                      <Edit size={16} />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => row.id && handleDelete(row.id)}
                    >
                      <Trash2 size={16} />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {data.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                    Brak zdefiniowanych napędów. Dodaj pierwsze wpisy.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={modalOpen} onClose={handleClose} fullWidth maxWidth="sm">
        <DialogTitle>{editingId ? "Edytuj Napęd" : "Nowy Napęd"}</DialogTitle>
        <DialogContent dividers sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <TextField
            label="Nazwa Napędu (np. Benzyna (PB))"
            size="small"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            autoFocus
          />
          <TextField
            select
            label="Kategoria"
            size="small"
            value={formData.category}
            onChange={(e) => setFormData({ ...formData, category: e.target.value })}
          >
            {CATEGORIES.map((cat) => (
              <MenuItem key={cat} value={cat}>
                {cat}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Opis (opcjonalny)"
            size="small"
            multiline
            rows={2}
            value={formData.description || ""}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Anuluj</Button>
          <Button variant="contained" onClick={handleSave} disabled={!formData.name}>
            Zapisz
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

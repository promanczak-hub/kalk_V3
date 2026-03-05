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

const BASE_URL = "http://127.0.0.1:8000";

const VEHICLE_CLASSES = ["Osobowy", "Dostawczy"] as const;

interface BodyTypeItem {
  id?: number;
  name: string;
  vehicle_class: string;
  description?: string;
}

function getClassColor(vc: string): "primary" | "warning" | "default" {
  if (vc === "Osobowy") return "primary";
  if (vc === "Dostawczy") return "warning";
  return "default";
}

export default function BodyTypesCrudPanel() {
  const [data, setData] = useState<BodyTypeItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [formData, setFormData] = useState<BodyTypeItem>({
    name: "",
    vehicle_class: VEHICLE_CLASSES[0],
    description: "",
  });
  const [editingId, setEditingId] = useState<number | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${BASE_URL}/api/body-types`);
      if (resp.ok) {
        const json = await resp.json();
        if (Array.isArray(json)) setData(json);
      }
    } catch (e) {
      console.error("Failed to load body types:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleOpen = (item?: BodyTypeItem) => {
    if (item) {
      setFormData(item);
      setEditingId(item.id || null);
    } else {
      setFormData({
        name: "",
        vehicle_class: VEHICLE_CLASSES[0],
        description: "",
      });
      setEditingId(null);
    }
    setModalOpen(true);
  };

  const handleClose = () => setModalOpen(false);

  const handleSave = async () => {
    try {
      const resp = await fetch(`${BASE_URL}/api/body-types`, {
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
    if (!confirm("Na pewno usunąć ten typ nadwozia?")) return;
    try {
      const resp = await fetch(`${BASE_URL}/api/body-types/${id}`, {
        method: "DELETE",
      });
      if (resp.ok) {
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  /* Group by vehicle_class for display */
  const grouped = VEHICLE_CLASSES.map((vc) => ({
    label: vc,
    items: data.filter((d) => d.vehicle_class === vc),
  }));

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h6">Słownik Typów Nadwozia</Typography>
        <Button
          variant="contained"
          startIcon={<Plus size={16} />}
          onClick={() => handleOpen()}
        >
          Dodaj Typ
        </Button>
      </Box>

      {loading ? (
        <CircularProgress />
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead sx={{ backgroundColor: "#f8fafc" }}>
              <TableRow>
                <TableCell>Typ Nadwozia</TableCell>
                <TableCell>Kategoria</TableCell>
                <TableCell>Opis</TableCell>
                <TableCell align="right">Akcje</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {grouped.map((group) => [
                <TableRow key={`header-${group.label}`}>
                  <TableCell
                    colSpan={4}
                    sx={{
                      bgcolor: "rgba(0,0,0,0.04)",
                      fontWeight: 700,
                      fontSize: "0.8rem",
                    }}
                  >
                    {group.label === "Osobowy" ? "🚗" : "🚛"} {group.label} (
                    {group.items.length})
                  </TableCell>
                </TableRow>,
                ...group.items.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell sx={{ fontWeight: 500, pl: 4 }}>
                      {row.name}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={row.vehicle_class}
                        size="small"
                        color={getClassColor(row.vehicle_class)}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>{row.description || "—"}</TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={() => handleOpen(row)}
                        color="primary"
                      >
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
                )),
              ])}
              {data.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={4}
                    align="center"
                    sx={{ py: 3, color: "text.secondary" }}
                  >
                    Brak zdefiniowanych typów nadwozia. Dodaj pierwsze wpisy.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={modalOpen} onClose={handleClose} fullWidth maxWidth="sm">
        <DialogTitle>
          {editingId ? "Edytuj Typ Nadwozia" : "Nowy Typ Nadwozia"}
        </DialogTitle>
        <DialogContent
          dividers
          sx={{ display: "flex", flexDirection: "column", gap: 2 }}
        >
          <TextField
            label="Nazwa (np. Hatchback, Furgon)"
            size="small"
            value={formData.name}
            onChange={(e) =>
              setFormData({ ...formData, name: e.target.value })
            }
            autoFocus
          />
          <TextField
            select
            label="Kategoria pojazdu"
            size="small"
            value={formData.vehicle_class}
            onChange={(e) =>
              setFormData({ ...formData, vehicle_class: e.target.value })
            }
          >
            {VEHICLE_CLASSES.map((vc) => (
              <MenuItem key={vc} value={vc}>
                {vc}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Opis (opcjonalny)"
            size="small"
            multiline
            rows={2}
            value={formData.description || ""}
            onChange={(e) =>
              setFormData({ ...formData, description: e.target.value })
            }
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Anuluj</Button>
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={!formData.name || !formData.vehicle_class}
          >
            Zapisz
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

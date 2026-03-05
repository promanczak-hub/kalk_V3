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
} from "@mui/material";
import { Edit, Trash2, Plus } from "lucide-react";

interface SamarClass {
  id: number;
  name: string;
  example_models?: string;
}

interface ReplacementCarRate {
  id?: string;
  samar_class_id: number;
  samar_class_name: string;
  average_days_per_year: number;
  daily_rate_net: number;
}

export default function ReplacementCarCrudPanel() {
  const [data, setData] = useState<ReplacementCarRate[]>([]);
  const [samarClasses, setSamarClasses] = useState<SamarClass[]>([]);
  const [loading, setLoading] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const [formData, setFormData] = useState<ReplacementCarRate>({
    samar_class_id: 0,
    samar_class_name: "",
    average_days_per_year: 6.5,
    daily_rate_net: 100,
  });

  useEffect(() => {
    fetchDependencies();
    fetchData();
  }, []);

  const fetchDependencies = async () => {
    try {
      const classesRes = await fetch(
        `http://127.0.0.1:8000/api/samar-classes`
      ).catch(() => null);
      if (classesRes?.ok) {
        setSamarClasses(await classesRes.json());
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const resp = await fetch(
        `http://127.0.0.1:8000/api/replacement-car-rates`
      );
      if (resp.ok) {
        setData(await resp.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const getClassName = (id: number) => {
    const found = samarClasses.find((c) => c.id === id);
    return found ? found.name : `Klasa ID: ${id}`;
  };

  const handleOpen = (item?: ReplacementCarRate) => {
    if (item) {
      setFormData(item);
      setEditingId(item.id || null);
    } else {
      const initialClassId =
        samarClasses.length > 0 ? samarClasses[0].id : 1;
      const initialClassName =
        samarClasses.length > 0 ? samarClasses[0].name : "";

      setFormData({
        samar_class_id: initialClassId,
        samar_class_name: initialClassName,
        average_days_per_year: 6.5,
        daily_rate_net: 100,
      });
      setEditingId(null);
    }
    setModalOpen(true);
  };

  const handleClose = () => setModalOpen(false);

  const handleSave = async () => {
    try {
      const resp = await fetch(
        `http://127.0.0.1:8000/api/replacement-car-rates`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(formData),
        }
      );
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

  const handleDelete = async (id: string) => {
    if (!confirm("Na pewno usunąć?")) return;
    try {
      const resp = await fetch(
        `http://127.0.0.1:8000/api/replacement-car-rates/${id}`,
        { method: "DELETE" }
      );
      if (resp.ok) {
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Existing samar_class_ids already in the data (for filtering new entries)
  const usedClassIds = new Set(data.map((d) => d.samar_class_id));

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h6">
          Stawki Samochodu Zastępczego (per klasa SAMAR)
        </Typography>
        <Button
          variant="contained"
          startIcon={<Plus size={16} />}
          onClick={() => handleOpen()}
        >
          Dodaj Stawkę
        </Button>
      </Box>

      {loading ? (
        <CircularProgress />
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead sx={{ backgroundColor: "#f8fafc" }}>
              <TableRow>
                <TableCell>Klasa SAMAR</TableCell>
                <TableCell>Nazwa klasy (DB)</TableCell>
                <TableCell align="right">
                  Średnia ilość dób w roku
                </TableCell>
                <TableCell align="right">Doba Netto (PLN)</TableCell>
                <TableCell align="right">
                  Roczny koszt netto (PLN)
                </TableCell>
                <TableCell align="right">Akcje</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.map((row) => (
                <TableRow key={row.id}>
                  <TableCell sx={{ fontWeight: 600 }}>
                    {getClassName(row.samar_class_id)}
                  </TableCell>
                  <TableCell sx={{ color: "text.secondary", fontSize: "0.85rem" }}>
                    {row.samar_class_name}
                  </TableCell>
                  <TableCell align="right">
                    {row.average_days_per_year}
                  </TableCell>
                  <TableCell align="right">
                    {row.daily_rate_net.toFixed(2)} zł
                  </TableCell>
                  <TableCell align="right" sx={{ color: "text.secondary" }}>
                    {(
                      row.average_days_per_year * row.daily_rate_net
                    ).toFixed(2)}{" "}
                    zł
                  </TableCell>
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
              ))}
              {data.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    align="center"
                    sx={{ py: 3, color: "text.secondary" }}
                  >
                    Brak stawek. Dodaj pierwsze wpisy lub uruchom seed.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={modalOpen} onClose={handleClose} fullWidth maxWidth="sm">
        <DialogTitle>
          {editingId
            ? "Edytuj Stawkę Zastępczego"
            : "Nowa Stawka Zastępczego"}
        </DialogTitle>
        <DialogContent
          dividers
          sx={{ display: "flex", flexDirection: "column", gap: 2 }}
        >
          <TextField
            select
            label="Klasa SAMAR"
            size="small"
            value={formData.samar_class_id}
            onChange={(e) => {
              const newId = parseInt(e.target.value);
              const cls = samarClasses.find((c) => c.id === newId);
              setFormData({
                ...formData,
                samar_class_id: newId,
                samar_class_name: cls?.name || "",
              });
            }}
          >
            {(samarClasses.length > 0
              ? samarClasses
              : [{ id: 1, name: "Klasa 1" }]
            ).map((c) => (
              <MenuItem
                key={c.id}
                value={c.id}
                disabled={!editingId && usedClassIds.has(c.id)}
              >
                {c.name}
                {!editingId && usedClassIds.has(c.id)
                  ? " (już przypisana)"
                  : ""}
              </MenuItem>
            ))}
          </TextField>

          <Box sx={{ display: "flex", gap: 2 }}>
            <TextField
              label="Średnia ilość dób w roku"
              type="number"
              size="small"
              fullWidth
              inputProps={{ step: 0.5, min: 0 }}
              value={formData.average_days_per_year}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  average_days_per_year: parseFloat(e.target.value) || 0,
                })
              }
            />
            <TextField
              label="Doba Netto (PLN)"
              type="number"
              size="small"
              fullWidth
              inputProps={{ step: 1, min: 0 }}
              value={formData.daily_rate_net}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  daily_rate_net: parseFloat(e.target.value) || 0,
                })
              }
            />
          </Box>

          {formData.average_days_per_year > 0 &&
            formData.daily_rate_net > 0 && (
              <Typography
                variant="body2"
                sx={{
                  color: "text.secondary",
                  mt: 1,
                  p: 1.5,
                  borderRadius: 1,
                  backgroundColor: "#f0f4ff",
                }}
              >
                Roczny koszt netto:{" "}
                <strong>
                  {(
                    formData.average_days_per_year * formData.daily_rate_net
                  ).toFixed(2)}{" "}
                  PLN
                </strong>{" "}
                | Miesięczny:{" "}
                <strong>
                  {(
                    (formData.average_days_per_year *
                      formData.daily_rate_net) /
                    12
                  ).toFixed(2)}{" "}
                  PLN
                </strong>
              </Typography>
            )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Anuluj</Button>
          <Button variant="contained" onClick={handleSave}>
            Zapisz
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

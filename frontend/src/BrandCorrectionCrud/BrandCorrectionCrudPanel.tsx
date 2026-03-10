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
  MenuItem,
  IconButton,
  CircularProgress,
  Chip,
  Autocomplete,
} from "@mui/material";
import { Edit, Trash2, Plus } from "lucide-react";

import { apiFetch } from "../lib/api";

interface SamarClass {
  id: number;
  name: string;
}

interface Engine {
  id: number;
  name: string;
  category: string;
}

interface BrandCorrection {
  id?: number;
  samar_class_id: number;
  rodzaj_paliwa: number;
  brand_name: string;
  model_name: string | null;
  korekta_procent: number;
  notes: string | null;
}

const EMPTY_FORM: BrandCorrection = {
  samar_class_id: 0,
  rodzaj_paliwa: 0,
  brand_name: "",
  model_name: null,
  korekta_procent: 0,
  notes: null,
};

function pctColor(pct: number): "success" | "error" | "default" {
  if (pct > 0) return "success";
  if (pct < 0) return "error";
  return "default";
}

interface Props {
  samarClassId?: number;
}

export default function BrandCorrectionCrudPanel({ samarClassId }: Props) {
  const [corrections, setCorrections] = useState<BrandCorrection[]>([]);
  const [samarClasses, setSamarClasses] = useState<SamarClass[]>([]);
  const [engines, setEngines] = useState<Engine[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<BrandCorrection>({ ...EMPTY_FORM });
  const [filterBrand, setFilterBrand] = useState("");
  const [filterClass, setFilterClass] = useState<number | "">(samarClassId ?? "");

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [corRes, clsRes, engRes] = await Promise.all([
        apiFetch(`/api/brand-corrections`),
        apiFetch(`/api/samar-classes`),
        apiFetch(`/api/engines`),
      ]);
      setCorrections(await corRes.json());
      setSamarClasses(await clsRes.json());
      setEngines(await engRes.json());
    } catch (e) {
      console.error("Fetch error:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Sync filterClass when parent samarClassId changes
  useEffect(() => {
    if (samarClassId !== undefined) {
      setFilterClass(samarClassId);
    }
  }, [samarClassId]);

  const classMap = Object.fromEntries(
    samarClasses.map((c) => [c.id, c.name])
  );
  const engineMap = Object.fromEntries(engines.map((e) => [e.id, e.name]));

  const uniqueBrands = [
    ...new Set(corrections.map((c) => c.brand_name).filter(Boolean)),
  ].sort();

  const filtered = corrections.filter((c) => {
    if (filterBrand && c.brand_name !== filterBrand) return false;
    if (filterClass !== "" && c.samar_class_id !== filterClass) return false;
    return true;
  });

  const handleOpen = (item?: BrandCorrection) => {
    setForm(item ? { ...item } : { ...EMPTY_FORM });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      const res = await apiFetch(`/api/brand-corrections`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(await res.text());
      setDialogOpen(false);
      fetchAll();
    } catch (e) {
      alert("Błąd zapisu: " + e);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Usunąć tę korektę?")) return;
    try {
      await apiFetch(`/api/brand-corrections/${id}`, {
        method: "DELETE",
      });
      fetchAll();
    } catch (e) {
      alert("Błąd usuwania: " + e);
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 2,
        }}
      >
        <Typography variant="h6">
          Korekty Marki / Modelu ({filtered.length} / {corrections.length})
        </Typography>
        <Button
          variant="contained"
          startIcon={<Plus size={16} />}
          onClick={() => handleOpen()}
        >
          Dodaj korektę
        </Button>
      </Box>

      {/* Filtry */}
      <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
        <Autocomplete
          size="small"
          sx={{ minWidth: 200 }}
          options={uniqueBrands}
          value={filterBrand || null}
          onChange={(_, v) => setFilterBrand(v || "")}
          renderInput={(params) => (
            <TextField {...params} label="Filtruj markę" />
          )}
        />
        <TextField
          select
          size="small"
          sx={{ minWidth: 200 }}
          label="Filtruj klasę SAMAR"
          value={filterClass}
          onChange={(e) => {
            const v = e.target.value as string | number;
            setFilterClass(v === "" ? "" : Number(v));
          }}
        >
          <MenuItem value="">— Wszystkie —</MenuItem>
          {samarClasses.map((c) => (
            <MenuItem key={c.id} value={c.id}>
              {c.name}
            </MenuItem>
          ))}
        </TextField>
      </Box>

      {/* Tabela */}
      <TableContainer component={Paper} sx={{ maxHeight: 600 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Klasa SAMAR</TableCell>
              <TableCell>Silnik</TableCell>
              <TableCell>Marka</TableCell>
              <TableCell>Model</TableCell>
              <TableCell align="right">Korekta %</TableCell>
              <TableCell>Notatki</TableCell>
              <TableCell align="center" sx={{ width: 90 }}>
                Akcje
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  Brak korekt. Dodaj pierwsze wpisy.
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((c) => (
                <TableRow key={c.id} hover>
                  <TableCell sx={{ fontSize: 13 }}>
                    {classMap[c.samar_class_id] || `ID:${c.samar_class_id}`}
                  </TableCell>
                  <TableCell sx={{ fontSize: 13 }}>
                    {engineMap[c.rodzaj_paliwa] || `ID:${c.rodzaj_paliwa}`}
                  </TableCell>
                  <TableCell>
                    <strong>{c.brand_name}</strong>
                  </TableCell>
                  <TableCell sx={{ color: c.model_name ? "inherit" : "#999" }}>
                    {c.model_name || "—"}
                  </TableCell>
                  <TableCell align="right">
                    <Chip
                      size="small"
                      color={pctColor(c.korekta_procent)}
                      label={`${c.korekta_procent > 0 ? "+" : ""}${(
                        c.korekta_procent * 100
                      ).toFixed(1)}%`}
                    />
                  </TableCell>
                  <TableCell sx={{ color: "#888", fontSize: 12 }}>
                    {c.notes || ""}
                  </TableCell>
                  <TableCell align="center">
                    <IconButton size="small" onClick={() => handleOpen(c)}>
                      <Edit size={14} />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => c.id && handleDelete(c.id)}
                    >
                      <Trash2 size={14} />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {form.id ? "Edytuj korektę marki" : "Nowa korekta marki"}
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            select
            label="Klasa SAMAR"
            value={form.samar_class_id || ""}
            onChange={(e) =>
              setForm({ ...form, samar_class_id: Number(e.target.value) })
            }
            required
            fullWidth
            margin="dense"
          >
            {samarClasses.map((c) => (
              <MenuItem key={c.id} value={c.id}>
                {c.name}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            select
            label="Silnik"
            value={form.rodzaj_paliwa || ""}
            onChange={(e) =>
              setForm({ ...form, rodzaj_paliwa: Number(e.target.value) })
            }
            required
            fullWidth
            margin="dense"
          >
            {engines.map((eng) => (
              <MenuItem key={eng.id} value={eng.id}>
                {eng.name}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            label="Marka (np. TOYOTA)"
            value={form.brand_name}
            onChange={(e) =>
              setForm({ ...form, brand_name: e.target.value.toUpperCase() })
            }
            required
            fullWidth
            margin="dense"
          />

          <TextField
            label="Model (opcjonalny, np. COROLLA)"
            value={form.model_name || ""}
            onChange={(e) =>
              setForm({
                ...form,
                model_name: e.target.value || null,
              })
            }
            fullWidth
            margin="dense"
            helperText="Puste = korekta dla całej marki"
          />

          <TextField
            label="Korekta % (np. -0.01 = -1%)"
            type="number"
            value={form.korekta_procent}
            onChange={(e) =>
              setForm({
                ...form,
                korekta_procent: parseFloat(e.target.value) || 0,
              })
            }
            required
            fullWidth
            margin="dense"
            inputProps={{ step: 0.001 }}
            helperText="Ujemna = auto traci, Dodatnia = auto zyskuje"
          />

          <TextField
            label="Notatki"
            value={form.notes || ""}
            onChange={(e) =>
              setForm({ ...form, notes: e.target.value || null })
            }
            fullWidth
            margin="dense"
            multiline
            rows={2}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Anuluj</Button>
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={
              !form.samar_class_id || !form.rodzaj_paliwa || !form.brand_name
            }
          >
            Zapisz
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

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
  TextField,
  MenuItem,
  IconButton,
  CircularProgress,
  Snackbar,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
} from "@mui/material";
import { Plus, Trash2, Info } from "lucide-react";

const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

interface BodyCorrection {
  id?: number;
  samar_class_id: number;
  brand_name: string | null;
  body_type_id: number | null;
  engine_type_id: number | null;
  correction_percent: number;
  zabudowa_correction_percent: number;
}

interface BodyType {
  id: number;
  name: string;
  vehicle_class: string;
}

interface Engine {
  id: number;
  name: string;
  category: string;
}

function scopeLabel(row: BodyCorrection, bodyTypes: BodyType[], engines: Engine[]): string {
  const parts: string[] = [];
  if (row.brand_name) parts.push(row.brand_name);
  else parts.push("Wszystkie marki");
  if (row.body_type_id) {
    const bt = bodyTypes.find((b) => b.id === row.body_type_id);
    parts.push(bt?.name || `body#${row.body_type_id}`);
  } else {
    parts.push("Wszystkie nadwozia");
  }
  if (row.engine_type_id) {
    const eng = engines.find((e) => e.id === row.engine_type_id);
    parts.push(eng?.name || `eng#${row.engine_type_id}`);
  } else {
    parts.push("Wszystkie silniki");
  }
  return parts.join(" → ");
}

function cascadeLevel(row: BodyCorrection): { label: string; color: string } {
  if (row.brand_name && row.body_type_id && row.engine_type_id)
    return { label: "EXACT", color: "#4caf50" };
  if (row.brand_name && row.body_type_id)
    return { label: "NO-ENG", color: "#ff9800" };
  if (row.brand_name)
    return { label: "NO-BODY", color: "#e91e63" };
  return { label: "GLOBAL", color: "#9c27b0" };
}

interface Props {
  samarClassId: number;
}

export default function BodyCorrectionsCrudPanel({ samarClassId }: Props) {
  const [corrections, setCorrections] = useState<BodyCorrection[]>([]);
  const [bodyTypes, setBodyTypes] = useState<BodyType[]>([]);
  const [engines, setEngines] = useState<Engine[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<BodyCorrection>({
    samar_class_id: samarClassId,
    brand_name: "",
    body_type_id: null,
    engine_type_id: null,
    correction_percent: 0,
    zabudowa_correction_percent: 0,
  });
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error";
  }>({ open: false, message: "", severity: "success" });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [corrResp, btResp, engResp] = await Promise.all([
        fetch(`${BASE_URL}/api/body-corrections?samar_class_id=${samarClassId}`),
        fetch(`${BASE_URL}/api/body-types`),
        fetch(`${BASE_URL}/api/engines`),
      ]);
      const corrData = corrResp.ok ? await corrResp.json() : [];
      const btData = btResp.ok ? await btResp.json() : [];
      const engData = engResp.ok ? await engResp.json() : [];
      setCorrections(Array.isArray(corrData) ? corrData : []);
      setBodyTypes(Array.isArray(btData) ? btData : []);
      setEngines(Array.isArray(engData) ? engData.sort((a: Engine, b: Engine) => a.id - b.id) : []);
    } catch (e) {
      console.error("Failed to load body corrections:", e);
    } finally {
      setLoading(false);
    }
  }, [samarClassId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAdd = () => {
    setForm({
      samar_class_id: samarClassId,
      brand_name: "",
      body_type_id: null,
      engine_type_id: null,
      correction_percent: 0,
      zabudowa_correction_percent: 0,
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    try {
      const payload = {
        ...form,
        samar_class_id: samarClassId,
        brand_name: form.brand_name?.trim().toUpperCase() || null,
        body_type_id: form.body_type_id || null,
        engine_type_id: form.engine_type_id || null,
      };
      const resp = await fetch(`${BASE_URL}/api/body-corrections`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (resp.ok) {
        setSnackbar({ open: true, message: "Korekta zapisana", severity: "success" });
        setModalOpen(false);
        fetchData();
      } else {
        const err = await resp.json();
        setSnackbar({
          open: true,
          message: err.detail || "Błąd zapisu",
          severity: "error",
        });
      }
    } catch (e) {
      console.error(e);
      setSnackbar({ open: true, message: "Błąd komunikacji", severity: "error" });
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Usunąć tę korektę?")) return;
    try {
      await fetch(`${BASE_URL}/api/body-corrections/${id}`, { method: "DELETE" });
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Box>
          <Typography variant="h6">Korekty Nadwozia (Sparse)</Typography>
          <Typography variant="caption" color="textSecondary">
            Tylko wyjątki — jeśli brak wpisu, korekta = 0%. Kaskada: EXACT → NO-ENG → NO-BODY → 0%.
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<Plus size={16} />} onClick={handleAdd}>
          Dodaj korektę
        </Button>
      </Box>

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
          <CircularProgress />
        </Box>
      ) : corrections.length === 0 ? (
        <Paper
          elevation={0}
          sx={{
            p: 4,
            textAlign: "center",
            borderRadius: 2,
            border: "2px dashed",
            borderColor: "divider",
          }}
        >
          <Typography variant="body1" sx={{ mb: 1, color: "text.secondary" }}>
            🚛 Brak korekt nadwozia dla tej klasy
          </Typography>
          <Typography variant="caption" color="textSecondary">
            Domyślna korekta = 0% dla wszystkich kombinacji marka × nadwozie × silnik.
            <br />
            Kliknij "Dodaj korektę" aby zdefiniować wyjątek.
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead sx={{ bgcolor: "rgba(0,0,0,0.04)" }}>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>Zakres</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Kaskada</TableCell>
                <TableCell align="center" sx={{ fontWeight: 700 }}>
                  Korekta %
                </TableCell>
                <TableCell align="center" sx={{ fontWeight: 700 }}>
                  Zabudowa %
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>
                  Akcje
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {corrections.map((row) => {
                const level = cascadeLevel(row);
                return (
                  <TableRow key={row.id} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {scopeLabel(row, bodyTypes, engines)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={level.label}
                        size="small"
                        sx={{
                          bgcolor: level.color,
                          color: "#fff",
                          fontWeight: 700,
                          fontSize: "0.65rem",
                        }}
                      />
                    </TableCell>
                    <TableCell align="center">
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: 700,
                          color:
                            row.correction_percent > 0
                              ? "#c62828"
                              : row.correction_percent < 0
                                ? "#2e7d32"
                                : "text.secondary",
                        }}
                      >
                        {(row.correction_percent * 100).toFixed(2)}%
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: 700,
                          color:
                            row.zabudowa_correction_percent > 0
                              ? "#c62828"
                              : row.zabudowa_correction_percent < 0
                                ? "#2e7d32"
                                : "text.secondary",
                        }}
                      >
                        {(row.zabudowa_correction_percent * 100).toFixed(2)}%
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => row.id && handleDelete(row.id)}
                      >
                        <Trash2 size={16} />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Box sx={{ mt: 2, p: 1.5, borderRadius: 1, bgcolor: "rgba(25,118,210,0.04)", border: "1px solid rgba(25,118,210,0.15)" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.5 }}>
          <Info size={14} />
          <Typography variant="caption" sx={{ fontWeight: 700 }}>Jak działa kaskada?</Typography>
        </Box>
        <Typography variant="caption" color="textSecondary" sx={{ lineHeight: 1.6 }}>
          Podczas kalkulacji system szuka korekty w kolejności: <b>EXACT</b> (marka+nadwozie+silnik) →{" "}
          <b>NO-ENG</b> (marka+nadwozie) → <b>NO-BODY</b> (tylko marka) → <b>DEFAULT 0%</b>.
          <br />
          Przykład: wpis "BMW → SUV → Diesel = +2%" dopasuje BMW X5 Diesel. BMW X5 Benzyna będzie szukać dalej.
        </Typography>
      </Box>

      {/* ── Add correction modal ── */}
      <Dialog open={modalOpen} onClose={() => setModalOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Nowa korekta nadwozia</DialogTitle>
        <DialogContent dividers sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <TextField
            label="Marka (UPPER, np. BMW)"
            size="small"
            value={form.brand_name || ""}
            onChange={(e) => setForm({ ...form, brand_name: e.target.value })}
            helperText="Zostaw puste = dotyczy WSZYSTKICH marek"
            autoFocus
          />
          <TextField
            select
            label="Typ nadwozia"
            size="small"
            value={form.body_type_id || ""}
            onChange={(e) =>
              setForm({ ...form, body_type_id: e.target.value ? Number(e.target.value) : null })
            }
            helperText="Zostaw puste = dotyczy WSZYSTKICH nadwozi"
          >
            <MenuItem value="">— Wszystkie nadwozia —</MenuItem>
            {bodyTypes.map((bt) => (
              <MenuItem key={bt.id} value={bt.id}>
                {bt.name} ({bt.vehicle_class})
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Silnik"
            size="small"
            value={form.engine_type_id || ""}
            onChange={(e) =>
              setForm({ ...form, engine_type_id: e.target.value ? Number(e.target.value) : null })
            }
            helperText="Zostaw puste = dotyczy WSZYSTKICH silników"
          >
            <MenuItem value="">— Wszystkie silniki —</MenuItem>
            {engines.map((eng) => (
              <MenuItem key={eng.id} value={eng.id}>
                {eng.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Korekta % (np. 2.5 = 2.5%)"
            size="small"
            type="number"
            value={form.correction_percent * 100}
            onChange={(e) =>
              setForm({ ...form, correction_percent: parseFloat(e.target.value || "0") / 100 })
            }
            helperText="Dodatnia = deprecjacja, ujemna = aprecjacja"
          />
          <TextField
            label="Zabudowa % (np. 4 = 4%)"
            size="small"
            type="number"
            value={form.zabudowa_correction_percent * 100}
            onChange={(e) =>
              setForm({
                ...form,
                zabudowa_correction_percent: parseFloat(e.target.value || "0") / 100,
              })
            }
            helperText="Korekta za specjalną zabudowę (np. kontener chłodniczy)"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setModalOpen(false)}>Anuluj</Button>
          <Button variant="contained" onClick={handleSave}>
            Zapisz
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
      >
        <Alert severity={snackbar.severity} variant="filled">
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

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
} from "@mui/material";
import { Edit, Trash2, Plus } from "lucide-react";

interface SamarClass {
  id: number;
  name: string;
  example_models?: string;
}

interface BrandCorrection {
  id?: string;
  klasa_samar: string;
  rodzaj_paliwa: string;
  marka: string;
  correction_percent: number;
}

interface EngineOption {
  id: number;
  name: string;
  category: string;
  fuel_group_id: number;
}

function getSeverity(pct: number): "green" | "orange" | "red" {
  if (pct >= 0) return "green";
  if (pct >= -5) return "orange";
  return "red";
}

function getSeverityLabel(pct: number): string {
  const severity = getSeverity(pct);
  if (severity === "green") return "Aprecjacja / Neutralna";
  if (severity === "orange") return "Lekka deprecjacja";
  return "Silna restrykcja";
}

export default function BrandCorrectionCrudPanel() {
  const [data, setData] = useState<BrandCorrection[]>([]);
  const [samarClasses, setSamarClasses] = useState<SamarClass[]>([]);
  const [engines, setEngines] = useState<EngineOption[]>([]);
  const [loading, setLoading] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const [formData, setFormData] = useState<BrandCorrection>({
    klasa_samar: "",
    rodzaj_paliwa: "Benzyna",
    marka: "",
    correction_percent: 0,
  });

  const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

  const fetchDependencies = useCallback(async () => {
    try {
      const [classesResp, enginesResp] = await Promise.all([
        fetch(`${baseUrl}/api/samar-classes`).catch(() => null),
        fetch(`${baseUrl}/api/engines`).catch(() => null),
      ]);
      if (classesResp?.ok) {
        setSamarClasses(await classesResp.json());
      }
      if (enginesResp?.ok) {
        setEngines(await enginesResp.json());
      }
    } catch (e) {
      console.error("Błąd pobierania zależności:", e);
    }
  }, [baseUrl]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${baseUrl}/api/brand-corrections`);
      if (resp.ok) {
        setData(await resp.json());
      }
    } catch (e) {
      console.error("Błąd pobierania korekt marki:", e);
    } finally {
      setLoading(false);
    }
  }, [baseUrl]);

  useEffect(() => {
    fetchDependencies();
    fetchData();
  }, [fetchDependencies, fetchData]);

  const getExampleModels = (className: string): string => {
    const found = samarClasses.find((c) => c.name === className);
    return found?.example_models || "";
  };

  const handleOpen = (item?: BrandCorrection) => {
    if (item) {
      setFormData(item);
      setEditingId(item.id || null);
    } else {
      const initialClass =
        samarClasses.length > 0 ? samarClasses[0].name : "B";
      setFormData({
        klasa_samar: initialClass,
        rodzaj_paliwa: "Benzyna",
        marka: "",
        correction_percent: 0,
      });
      setEditingId(null);
    }
    setModalOpen(true);
  };

  const handleClose = () => setModalOpen(false);

  const handleSave = async () => {
    if (!formData.marka.trim()) {
      alert("Pole 'Marka / Model' jest wymagane.");
      return;
    }
    try {
      const resp = await fetch(`${baseUrl}/api/brand-corrections`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      if (resp.ok) {
        fetchData();
        handleClose();
      } else {
        const err = await resp.json().catch(() => ({}));
        alert(`Błąd zapisu: ${err.detail || "Nieznany błąd"}`);
      }
    } catch (e) {
      console.error(e);
      alert("Błąd komunikacji z serwerem.");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Na pewno usunąć tę korektę?")) return;
    try {
      const resp = await fetch(`${baseUrl}/api/brand-corrections/${id}`, {
        method: "DELETE",
      });
      if (resp.ok) {
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Group data by klasa_samar for organized display
  const groupedByClass = data.reduce(
    (acc, item) => {
      if (!acc[item.klasa_samar]) {
        acc[item.klasa_samar] = [];
      }
      acc[item.klasa_samar].push(item);
      return acc;
    },
    {} as Record<string, BrandCorrection[]>,
  );

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Box>
          <Typography variant="h6">
            Korekta WR za Markę / Model
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Aprecjacja (+) lub deprecjacja (-) Wartości Rezydualnej per klasa
            SAMAR. Np. „Volkswagen Crafter" w klasie Bvan może mieć inną korektę
            niż w klasie B.
          </Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 1, alignItems: "flex-start" }}>
          <Button
            variant="contained"
            startIcon={<Plus size={16} />}
            onClick={() => handleOpen()}
          >
            Dodaj Korektę
          </Button>
        </Box>
      </Box>

      {loading ? (
        <CircularProgress />
      ) : data.length === 0 ? (
        <Paper
          variant="outlined"
          sx={{ p: 4, textAlign: "center", color: "text.secondary" }}
        >
          <Typography>
            Brak zdefiniowanych korekt za markę. Dodaj pierwsze wpisy.
          </Typography>
        </Paper>
      ) : (
        Object.entries(groupedByClass)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([className, items]) => (
            <Box key={className} sx={{ mb: 3 }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1.5,
                  mb: 1,
                }}
              >
                <Typography
                  variant="subtitle1"
                  fontWeight="bold"
                  color="primary"
                >
                  Klasa: {className}
                </Typography>
                {getExampleModels(className) && (
                  <Typography variant="caption" color="text.secondary">
                    ({getExampleModels(className)})
                  </Typography>
                )}
              </Box>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead sx={{ backgroundColor: "#f8fafc" }}>
                    <TableRow>
                      <TableCell>Marka / Model</TableCell>
                      <TableCell>Rodzaj Paliwa</TableCell>
                      <TableCell align="right">Korekta WR (%)</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell align="right">Akcje</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {items.map((row) => {
                      const severity = getSeverity(row.correction_percent);
                      return (
                        <TableRow key={row.id}>
                          <TableCell sx={{ fontWeight: 500 }}>
                            {row.marka}
                          </TableCell>
                          <TableCell>{row.rodzaj_paliwa}</TableCell>
                          <TableCell align="right">
                            <Typography
                              component="span"
                              sx={{
                                fontWeight: 600,
                                color:
                                  severity === "green"
                                    ? "success.main"
                                    : severity === "orange"
                                      ? "warning.main"
                                      : "error.main",
                              }}
                            >
                              {row.correction_percent > 0 ? "+" : ""}
                              {row.correction_percent}%
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={getSeverityLabel(row.correction_percent)}
                              color={
                                severity === "green"
                                  ? "success"
                                  : severity === "orange"
                                    ? "warning"
                                    : "error"
                              }
                              variant="outlined"
                              sx={{ fontSize: "0.7rem" }}
                            />
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
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          ))
      )}

      {/* Add / Edit Dialog */}
      <Dialog open={modalOpen} onClose={handleClose} fullWidth maxWidth="sm">
        <DialogTitle>
          {editingId ? "Edytuj Korektę Marki" : "Nowa Korekta Marki"}
        </DialogTitle>
        <DialogContent
          dividers
          sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}
        >
          <TextField
            label="Marka / Model"
            size="small"
            fullWidth
            value={formData.marka}
            onChange={(e) =>
              setFormData({ ...formData, marka: e.target.value })
            }
            placeholder="np. Volkswagen Crafter, BMW, Toyota Corolla"
            helperText="Wpisz markę lub markę+model. LLM dopasuje automatycznie do tego wpisu."
          />

          <TextField
            select
            label="Klasa SAMAR"
            size="small"
            value={formData.klasa_samar}
            onChange={(e) =>
              setFormData({ ...formData, klasa_samar: e.target.value })
            }
          >
            {samarClasses.length > 0 ? (
              samarClasses.map((c) => (
                <MenuItem key={c.id} value={c.name}>
                  {c.name}
                  {c.example_models ? ` — ${c.example_models}` : ""}
                </MenuItem>
              ))
            ) : (
              <MenuItem value="B">B (ładowanie...)</MenuItem>
            )}
          </TextField>

          <TextField
            select
            label="Rodzaj Napędu"
            size="small"
            value={formData.rodzaj_paliwa}
            onChange={(e) =>
              setFormData({ ...formData, rodzaj_paliwa: e.target.value })
            }
          >
            {engines.length > 0 ? (
              engines.map((eng) => (
                <MenuItem key={eng.id} value={eng.name}>
                  {eng.name}
                </MenuItem>
              ))
            ) : (
              <MenuItem disabled>Ładowanie...</MenuItem>
            )}
          </TextField>

          <TextField
            label="Korekta WR (%)"
            type="number"
            size="small"
            fullWidth
            inputProps={{ step: 0.5, min: -100, max: 100 }}
            value={formData.correction_percent}
            onChange={(e) =>
              setFormData({
                ...formData,
                correction_percent: parseFloat(e.target.value) || 0,
              })
            }
            helperText="Wartość ujemna = deprecjacja (🔴), dodatnia = aprecjacja (🟢). Np. -3 oznacza -3% korekty WR."
          />

          {/* Preview severity */}
          <Box
            sx={{
              p: 1.5,
              borderRadius: 1,
              bgcolor:
                getSeverity(formData.correction_percent) === "green"
                  ? "success.50"
                  : getSeverity(formData.correction_percent) === "orange"
                    ? "warning.50"
                    : "error.50",
              border: 1,
              borderColor:
                getSeverity(formData.correction_percent) === "green"
                  ? "success.200"
                  : getSeverity(formData.correction_percent) === "orange"
                    ? "warning.200"
                    : "error.200",
            }}
          >
            <Typography variant="body2" fontWeight={500}>
              Podgląd: {formData.marka || "?"} w klasie {formData.klasa_samar} →{" "}
              {getSeverity(formData.correction_percent) === "green"
                ? "🟢"
                : getSeverity(formData.correction_percent) === "orange"
                  ? "🟡"
                  : "🔴"}{" "}
              {getSeverityLabel(formData.correction_percent)} (
              {formData.correction_percent > 0 ? "+" : ""}
              {formData.correction_percent}%)
            </Typography>
          </Box>
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

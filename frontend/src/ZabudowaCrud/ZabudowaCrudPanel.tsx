import { useState, useEffect } from "react";
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  TextField,
  Button,
  Chip,
  alpha,
  useTheme,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Select,
  MenuItem,
  InputLabel,
  FormControl,
  Tooltip,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import SaveIcon from "@mui/icons-material/Save";

const BASE_URL = import.meta.env.VITE_API_URL || "";

interface ZabudowaType {
  id?: number;
  name: string;
  description?: string;
  excel_code?: string;
}

interface ZabudowaCorrection {
  id?: number;
  zabudowa_type_id: number;
  samar_class_id: number | null;
  correction_percent: number;
}

interface SamarClass {
  id: number;
  name: string;
}

export default function ZabudowaCrudPanel() {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";

  const [types, setTypes] = useState<ZabudowaType[]>([]);
  const [corrections, setCorrections] = useState<ZabudowaCorrection[]>([]);
  const [samarClasses, setSamarClasses] = useState<SamarClass[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingType, setEditingType] = useState<ZabudowaType | null>(null);
  const [corrDialogOpen, setCorrDialogOpen] = useState(false);
  const [editingCorr, setEditingCorr] = useState<ZabudowaCorrection | null>(null);
  const [form, setForm] = useState<ZabudowaType>({ name: "", description: "", excel_code: "" });
  const [corrForm, setCorrForm] = useState<ZabudowaCorrection>({
    zabudowa_type_id: 0,
    samar_class_id: null,
    correction_percent: 0,
  });

  const accent = "#6d4c41";

  const fetchAll = () => {
    fetch(`${BASE_URL}/api/zabudowa-types`)
      .then((r) => r.json())
      .then(setTypes)
      .catch(console.error);
    fetch(`${BASE_URL}/api/zabudowa-corrections`)
      .then((r) => r.json())
      .then(setCorrections)
      .catch(console.error);
    fetch(`${BASE_URL}/api/samar-classes`)
      .then((r) => r.json())
      .then(setSamarClasses)
      .catch(console.error);
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleSaveType = async () => {
    try {
      const payload = editingType ? { ...form, id: editingType.id } : form;
      await fetch(`${BASE_URL}/api/zabudowa-types`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setDialogOpen(false);
      setEditingType(null);
      setForm({ name: "", description: "", excel_code: "" });
      fetchAll();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteType = async (id: number) => {
    if (!confirm("Usunąć typ zabudowy? Powiązane korekty zostaną usunięte.")) return;
    try {
      await fetch(`${BASE_URL}/api/zabudowa-types/${id}`, { method: "DELETE" });
      fetchAll();
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveCorr = async () => {
    try {
      const payload = editingCorr ? { ...corrForm, id: editingCorr.id } : corrForm;
      await fetch(`${BASE_URL}/api/zabudowa-corrections`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setCorrDialogOpen(false);
      setEditingCorr(null);
      setCorrForm({ zabudowa_type_id: 0, samar_class_id: null, correction_percent: 0 });
      fetchAll();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteCorr = async (id: number) => {
    if (!confirm("Usunąć korektę?")) return;
    try {
      await fetch(`${BASE_URL}/api/zabudowa-corrections/${id}`, { method: "DELETE" });
      fetchAll();
    } catch (err) {
      console.error(err);
    }
  };

  const getTypeName = (id: number) => types.find((t) => t.id === id)?.name || `ID:${id}`;
  const getClassName = (id: number | null) =>
    id === null ? "📌 Globalna (wszystkie klasy)" : samarClasses.find((c) => c.id === id)?.name || `ID:${id}`;

  return (
    <Box>
      {/* ── Section 1: Zabudowa Types Dictionary ── */}
      <Paper
        elevation={0}
        sx={{
          p: 2,
          mb: 3,
          borderRadius: 2,
          bgcolor: isDark ? alpha(accent, 0.08) : alpha(accent, 0.04),
          border: `1px solid ${alpha(accent, 0.3)}`,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
          <Typography sx={{ fontWeight: 700, fontSize: "0.95rem", color: accent }}>
            🏗️ Słownik typów zabudowy
          </Typography>
          <Button
            size="small"
            startIcon={<AddIcon />}
            onClick={() => {
              setEditingType(null);
              setForm({ name: "", description: "", excel_code: "" });
              setDialogOpen(true);
            }}
            sx={{ fontWeight: 600 }}
          >
            Nowy typ
          </Button>
        </Box>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: alpha(accent, isDark ? 0.1 : 0.04) }}>
                <TableCell sx={{ fontWeight: 700, width: 40 }}>ID</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Nazwa</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Opis</TableCell>
                <TableCell sx={{ fontWeight: 700, width: 80 }}>Kod Excel</TableCell>
                <TableCell sx={{ fontWeight: 700, width: 60 }}>Korekta</TableCell>
                <TableCell sx={{ fontWeight: 700, width: 80 }}>Akcje</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {types.map((t) => {
                const globalCorr = corrections.find(
                  (c) => c.zabudowa_type_id === t.id && c.samar_class_id === null
                );
                const corrPct = globalCorr ? globalCorr.correction_percent * 100 : 0;
                return (
                  <TableRow key={t.id} sx={{ "&:hover": { bgcolor: alpha(accent, 0.04) } }}>
                    <TableCell>
                      <Chip
                        label={t.id}
                        size="small"
                        sx={{ fontFamily: "monospace", fontWeight: 700, fontSize: "0.7rem", height: 22 }}
                      />
                    </TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>{t.name}</TableCell>
                    <TableCell sx={{ fontSize: "0.8rem", color: "text.secondary" }}>
                      {t.description || "—"}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={t.excel_code || "—"}
                        size="small"
                        variant="outlined"
                        sx={{ fontFamily: "monospace", fontSize: "0.7rem", height: 20 }}
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={`${corrPct > 0 ? "+" : ""}${corrPct.toFixed(1)}%`}
                        size="small"
                        sx={{
                          fontWeight: 700,
                          fontSize: "0.75rem",
                          height: 22,
                          bgcolor: corrPct > 0 ? alpha("#4caf50", 0.15) : alpha("#9e9e9e", 0.1),
                          color: corrPct > 0 ? "#2e7d32" : "text.secondary",
                        }}
                      />
                    </TableCell>
                    <TableCell>
                      <Tooltip title="Edytuj">
                        <IconButton
                          size="small"
                          onClick={() => {
                            setEditingType(t);
                            setForm({ name: t.name, description: t.description || "", excel_code: t.excel_code || "" });
                            setDialogOpen(true);
                          }}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Usuń">
                        <IconButton size="small" color="error" onClick={() => t.id && handleDeleteType(t.id)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* ── Section 2: Zabudowa WR Corrections ── */}
      <Paper
        elevation={0}
        sx={{
          p: 2,
          borderRadius: 2,
          bgcolor: isDark ? alpha("#e65100", 0.08) : alpha("#fff3e0", 0.5),
          border: `1px solid ${alpha("#e65100", 0.3)}`,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
          <Typography sx={{ fontWeight: 700, fontSize: "0.95rem", color: "#e65100" }}>
            📐 Korekty WR zabudowy
          </Typography>
          <Button
            size="small"
            startIcon={<AddIcon />}
            onClick={() => {
              setEditingCorr(null);
              setCorrForm({
                zabudowa_type_id: types[0]?.id || 0,
                samar_class_id: null,
                correction_percent: 0,
              });
              setCorrDialogOpen(true);
            }}
            sx={{ fontWeight: 600 }}
          >
            Dodaj korektę
          </Button>
        </Box>
        <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mb: 1 }}>
          „Globalna" = domyślna korekta dla wszystkich klas SAMAR. Korekta per klasa nadpisuje globalną.
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: alpha("#e65100", 0.06) }}>
                <TableCell sx={{ fontWeight: 700, width: 40 }}>ID</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Typ zabudowy</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Klasa SAMAR</TableCell>
                <TableCell sx={{ fontWeight: 700, width: 100 }}>Korekta %</TableCell>
                <TableCell sx={{ fontWeight: 700, width: 80 }}>Akcje</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {corrections.map((c) => (
                <TableRow key={c.id} sx={{ "&:hover": { bgcolor: alpha("#e65100", 0.04) } }}>
                  <TableCell sx={{ fontFamily: "monospace", fontSize: "0.75rem" }}>{c.id}</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>{getTypeName(c.zabudowa_type_id)}</TableCell>
                  <TableCell sx={{ fontSize: "0.8rem" }}>{getClassName(c.samar_class_id)}</TableCell>
                  <TableCell>
                    <Chip
                      label={`${(c.correction_percent * 100).toFixed(2)}%`}
                      size="small"
                      sx={{
                        fontWeight: 700,
                        fontSize: "0.75rem",
                        height: 22,
                        bgcolor:
                          c.correction_percent > 0
                            ? alpha("#4caf50", 0.15)
                            : c.correction_percent < 0
                              ? alpha("#f44336", 0.15)
                              : alpha("#9e9e9e", 0.1),
                        color:
                          c.correction_percent > 0
                            ? "#2e7d32"
                            : c.correction_percent < 0
                              ? "#c62828"
                              : "text.secondary",
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <Tooltip title="Edytuj">
                      <IconButton
                        size="small"
                        onClick={() => {
                          setEditingCorr(c);
                          setCorrForm({
                            zabudowa_type_id: c.zabudowa_type_id,
                            samar_class_id: c.samar_class_id,
                            correction_percent: c.correction_percent,
                          });
                          setCorrDialogOpen(true);
                        }}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Usuń">
                      <IconButton size="small" color="error" onClick={() => c.id && handleDeleteCorr(c.id)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* ── Dialog: Type Dictionary ── */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{editingType ? "Edytuj typ zabudowy" : "Nowy typ zabudowy"}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
            <TextField
              label="Nazwa"
              fullWidth
              size="small"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <TextField
              label="Opis"
              fullWidth
              size="small"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
            <TextField
              label="Kod Excel (P / Px)"
              fullWidth
              size="small"
              value={form.excel_code}
              onChange={(e) => setForm({ ...form, excel_code: e.target.value })}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Anuluj</Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSaveType}
            disabled={!form.name.trim()}
          >
            Zapisz
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Dialog: Correction ── */}
      <Dialog open={corrDialogOpen} onClose={() => setCorrDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{editingCorr ? "Edytuj korektę" : "Nowa korekta zabudowy"}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
            <FormControl fullWidth size="small">
              <InputLabel>Typ zabudowy</InputLabel>
              <Select
                label="Typ zabudowy"
                value={corrForm.zabudowa_type_id}
                onChange={(e) => setCorrForm({ ...corrForm, zabudowa_type_id: Number(e.target.value) })}
              >
                {types.map((t) => (
                  <MenuItem key={t.id} value={t.id}>
                    {t.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth size="small">
              <InputLabel>Klasa SAMAR (pusta = globalna)</InputLabel>
              <Select
                label="Klasa SAMAR (pusta = globalna)"
                value={corrForm.samar_class_id ?? ""}
                onChange={(e) => {
                  const val = e.target.value as string | number;
                  setCorrForm({
                    ...corrForm,
                    samar_class_id: val === "" ? null : Number(val),
                  });
                }}
              >
                <MenuItem value="">📌 Globalna (wszystkie klasy)</MenuItem>
                {samarClasses.map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="Korekta (%)"
              type="number"
              fullWidth
              size="small"
              value={corrForm.correction_percent * 100}
              onChange={(e) =>
                setCorrForm({
                  ...corrForm,
                  correction_percent: parseFloat(e.target.value || "0") / 100,
                })
              }
              helperText="Np. 4 = +4% do WR"
              inputProps={{ step: 0.5 }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCorrDialogOpen(false)}>Anuluj</Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSaveCorr}
            disabled={!corrForm.zabudowa_type_id}
          >
            Zapisz
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

import { useState, useEffect, useCallback } from "react";
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
  Chip,
  IconButton,
  Button,
  TextField,
  Select,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  alpha,
  useTheme,
  Tooltip,
  CircularProgress,
  Tabs,
  Tab,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import DownloadIcon from "@mui/icons-material/Download";
import UploadIcon from "@mui/icons-material/Upload";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface Category {
  id: number;
  category_key: string;
  display_name: string;
  vehicle_scope: string;
  sort_order: number;
  is_active: boolean;
}

interface Feature {
  id: number;
  category_id: number;
  feature_key: string;
  display_name: string;
  feature_type: string;
  vehicle_scope: string;
  sort_order: number;
  is_active: boolean;
  description: string | null;
  source_column_index: number | null;
  applicable_body_types: string[] | null;
}

const SCOPE_COLORS: Record<string, string> = {
  both: "#1976d2",
  commercial: "#e65100",
  passenger: "#2e7d32",
};

const SCOPE_LABELS: Record<string, string> = {
  both: "Oba",
  commercial: "Użytkowe",
  passenger: "Osobowe",
};

/* ─────────── Main Panel ─────────── */
export default function FeaturesCrudPanel() {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";
  const [tab, setTab] = useState(0);
  const [categories, setCategories] = useState<Category[]>([]);
  const [features, setFeatures] = useState<Feature[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Category edit dialog
  const [catDialog, setCatDialog] = useState(false);
  const [editingCat, setEditingCat] = useState<Partial<Category> | null>(null);

  // Feature edit dialog
  const [featDialog, setFeatDialog] = useState(false);
  const [editingFeat, setEditingFeat] = useState<Partial<Feature> | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [catsRes, featsRes] = await Promise.all([
        fetch(`${API}/api/features/admin/categories`),
        fetch(`${API}/api/features/admin/features`),
      ]);
      setCategories(await catsRes.json());
      setFeatures(await featsRes.json());
    } catch (e) {
      setError(`Błąd ładowania: ${e}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ── Handlers ──
  const handleDownload = async (type: "categories" | "features") => {
    const url = `${API}/api/features/admin/${type}/export-xlsx`;
    const res = await fetch(url);
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${type}_export.xlsx`;
    a.click();
  };

  const handleUpload = async (type: "categories" | "features", file: File) => {
    const url = `${API}/api/features/admin/${type}/import-xlsx`;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch(url, { method: "POST", body: fd });
      const data = await res.json();
      if (res.ok) {
        setSuccessMsg(`Import: ${data.inserted} wstawionych, ${data.errors?.length || 0} błędów`);
        fetchData();
      } else {
        setError(data.detail || "Import failed");
      }
    } catch (e) {
      setError(`Import error: ${e}`);
    }
  };

  const saveCat = async () => {
    if (!editingCat) return;
    try {
      await fetch(`${API}/api/features/admin/categories`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editingCat),
      });
      setCatDialog(false);
      setEditingCat(null);
      fetchData();
    } catch (e) {
      setError(`Save error: ${e}`);
    }
  };

  const deleteCat = async (id: number) => {
    if (!confirm("Usunąć kategorię?")) return;
    await fetch(`${API}/api/features/admin/categories/${id}`, { method: "DELETE" });
    fetchData();
  };

  const saveFeat = async () => {
    if (!editingFeat) return;
    try {
      await fetch(`${API}/api/features/admin/features`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editingFeat),
      });
      setFeatDialog(false);
      setEditingFeat(null);
      fetchData();
    } catch (e) {
      setError(`Save error: ${e}`);
    }
  };

  const deleteFeat = async (id: number) => {
    if (!confirm("Usunąć cechę?")) return;
    await fetch(`${API}/api/features/admin/features/${id}`, { method: "DELETE" });
    fetchData();
  };

  const getCatName = (id: number) => categories.find((c) => c.id === id)?.display_name || `#${id}`;
  const getCatColor = (scope: string) => SCOPE_COLORS[scope] || "#757575";

  // ── Render ──
  return (
    <Box>
      {/* Header with info */}
      <Paper
        elevation={0}
        sx={{
          p: 2, mb: 2, borderRadius: 2,
          bgcolor: isDark ? alpha("#0d47a1", 0.08) : alpha("#e3f2fd", 0.5),
          border: `1px solid ${isDark ? "#1565c0" : "#90caf9"}`,
        }}
      >
        <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
          🏷️ Zarządzanie Cechami Pojazdów — {categories.length} kategorii, {features.length} cech
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          CRUD + XLSX dla tabel reverse_search.universal_feature_categories / universal_features
        </Typography>
      </Paper>

      {/* Alerts */}
      {error && <Alert severity="error" onClose={() => setError("")} sx={{ mb: 1 }}>{error}</Alert>}
      {successMsg && <Alert severity="success" onClose={() => setSuccessMsg("")} sx={{ mb: 1 }}>{successMsg}</Alert>}

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
        <Tabs value={tab} onChange={(_e, v) => setTab(v)}>
          <Tab label={`📂 Kategorie (${categories.length})`} />
          <Tab label={`🏷️ Cechy (${features.length})`} />
        </Tabs>
      </Box>

      {loading && <CircularProgress sx={{ display: "block", mx: "auto", my: 4 }} />}

      {/* ── TAB 0: CATEGORIES ── */}
      {!loading && tab === 0 && (
        <Box>
          <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
            <Button variant="contained" size="small" startIcon={<AddIcon />}
              onClick={() => { setEditingCat({ category_key: "", display_name: "", vehicle_scope: "both", sort_order: 100, is_active: true }); setCatDialog(true); }}>
              Dodaj kategorię
            </Button>
            <Button variant="outlined" size="small" startIcon={<DownloadIcon />} onClick={() => handleDownload("categories")}>
              Export XLSX
            </Button>
            <Button variant="outlined" size="small" startIcon={<UploadIcon />} component="label">
              Import XLSX
              <input type="file" hidden accept=".xlsx" onChange={(e) => { if (e.target.files?.[0]) handleUpload("categories", e.target.files[0]); }} />
            </Button>
          </Box>
          <TableContainer component={Paper} elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ bgcolor: isDark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)" }}>
                  <TableCell sx={{ fontWeight: 700, width: 40 }}>ID</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Klucz</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Nazwa</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100 }}>Scope</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 60 }}>Order</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 80 }}>Cechy</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 80 }}>Akcje</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {categories.map((cat) => {
                  const featureCount = features.filter((f) => f.category_id === cat.id).length;
                  const scopeColor = getCatColor(cat.vehicle_scope);
                  return (
                    <TableRow key={cat.id} sx={{ "&:hover": { bgcolor: alpha(scopeColor, 0.04) } }}>
                      <TableCell>
                        <Chip label={cat.id} size="small" sx={{ fontFamily: "monospace", fontWeight: 700, fontSize: "0.7rem", height: 22 }} />
                      </TableCell>
                      <TableCell sx={{ fontFamily: "monospace", fontSize: "0.8rem" }}>{cat.category_key}</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>{cat.display_name}</TableCell>
                      <TableCell>
                        <Chip label={SCOPE_LABELS[cat.vehicle_scope] || cat.vehicle_scope} size="small"
                          sx={{ bgcolor: alpha(scopeColor, 0.12), color: scopeColor, fontWeight: 600, fontSize: "0.7rem", height: 22 }} />
                      </TableCell>
                      <TableCell sx={{ fontFamily: "monospace" }}>{cat.sort_order}</TableCell>
                      <TableCell>
                        <Chip label={featureCount} size="small" variant="outlined" sx={{ fontWeight: 700, fontSize: "0.75rem", height: 22 }} />
                      </TableCell>
                      <TableCell>
                        <Tooltip title="Edytuj">
                          <IconButton size="small" onClick={() => { setEditingCat({ ...cat }); setCatDialog(true); }}><EditIcon fontSize="small" /></IconButton>
                        </Tooltip>
                        <Tooltip title="Usuń">
                          <IconButton size="small" color="error" onClick={() => deleteCat(cat.id)}><DeleteIcon fontSize="small" /></IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* ── TAB 1: FEATURES ── */}
      {!loading && tab === 1 && (
        <Box>
          <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
            <Button variant="contained" size="small" startIcon={<AddIcon />}
              onClick={() => { setEditingFeat({ feature_key: "", display_name: "", category_id: categories[0]?.id || 0, feature_type: "boolean", vehicle_scope: "both", sort_order: 100, is_active: true }); setFeatDialog(true); }}>
              Dodaj cechę
            </Button>
            <Button variant="outlined" size="small" startIcon={<DownloadIcon />} onClick={() => handleDownload("features")}>
              Export XLSX
            </Button>
            <Button variant="outlined" size="small" startIcon={<UploadIcon />} component="label">
              Import XLSX
              <input type="file" hidden accept=".xlsx" onChange={(e) => { if (e.target.files?.[0]) handleUpload("features", e.target.files[0]); }} />
            </Button>
          </Box>
          <TableContainer component={Paper} elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2, maxHeight: 600 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700, width: 40 }}>ID</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Klucz</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Nazwa</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 120 }}>Kategoria</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 80 }}>Typ</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 80 }}>Scope</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 50 }}>Col</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 80 }}>Akcje</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {features.map((f) => {
                  const scopeColor = getCatColor(f.vehicle_scope);
                  return (
                    <TableRow key={f.id} sx={{ "&:hover": { bgcolor: alpha(scopeColor, 0.04) } }}>
                      <TableCell>
                        <Chip label={f.id} size="small" sx={{ fontFamily: "monospace", fontSize: "0.65rem", height: 20 }} />
                      </TableCell>
                      <TableCell sx={{ fontFamily: "monospace", fontSize: "0.75rem", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={f.feature_key}>
                        {f.feature_key}
                      </TableCell>
                      <TableCell sx={{ fontSize: "0.8rem", fontWeight: 500, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={f.display_name}>
                        {f.display_name}
                      </TableCell>
                      <TableCell>
                        <Chip label={getCatName(f.category_id)} size="small" variant="outlined" sx={{ fontSize: "0.65rem", height: 20, maxWidth: 110 }} />
                      </TableCell>
                      <TableCell>
                        <Chip label={f.feature_type} size="small"
                          sx={{
                            fontSize: "0.65rem", height: 20, fontFamily: "monospace",
                            bgcolor: f.feature_type === "boolean" ? alpha("#4caf50", 0.12) : f.feature_type === "numeric" ? alpha("#2196f3", 0.12) : alpha("#ff9800", 0.12),
                          }} />
                      </TableCell>
                      <TableCell>
                        <Chip label={SCOPE_LABELS[f.vehicle_scope] || f.vehicle_scope} size="small"
                          sx={{ bgcolor: alpha(scopeColor, 0.12), color: scopeColor, fontSize: "0.65rem", height: 20 }} />
                      </TableCell>
                      <TableCell sx={{ fontFamily: "monospace", fontSize: "0.75rem", color: "text.secondary" }}>
                        {f.source_column_index ?? "—"}
                      </TableCell>
                      <TableCell>
                        <Tooltip title="Edytuj">
                          <IconButton size="small" onClick={() => { setEditingFeat({ ...f }); setFeatDialog(true); }}><EditIcon fontSize="small" /></IconButton>
                        </Tooltip>
                        <Tooltip title="Usuń">
                          <IconButton size="small" color="error" onClick={() => deleteFeat(f.id)}><DeleteIcon fontSize="small" /></IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* ── Category Dialog ── */}
      <Dialog open={catDialog} onClose={() => setCatDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingCat?.id ? "Edytuj kategorię" : "Nowa kategoria"}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
          <TextField label="Klucz (category_key)" size="small" value={editingCat?.category_key || ""}
            onChange={(e) => setEditingCat({ ...editingCat, category_key: e.target.value })} />
          <TextField label="Nazwa wyświetlana" size="small" value={editingCat?.display_name || ""}
            onChange={(e) => setEditingCat({ ...editingCat, display_name: e.target.value })} />
          <Select size="small" value={editingCat?.vehicle_scope || "both"}
            onChange={(e) => setEditingCat({ ...editingCat, vehicle_scope: e.target.value })}>
            <MenuItem value="both">Oba (both)</MenuItem>
            <MenuItem value="commercial">Użytkowe (commercial)</MenuItem>
            <MenuItem value="passenger">Osobowe (passenger)</MenuItem>
          </Select>
          <TextField label="Sort order" size="small" type="number" value={editingCat?.sort_order ?? 100}
            onChange={(e) => setEditingCat({ ...editingCat, sort_order: Number(e.target.value) })} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCatDialog(false)}>Anuluj</Button>
          <Button variant="contained" onClick={saveCat}>Zapisz</Button>
        </DialogActions>
      </Dialog>

      {/* ── Feature Dialog ── */}
      <Dialog open={featDialog} onClose={() => setFeatDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingFeat?.id ? "Edytuj cechę" : "Nowa cecha"}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
          <TextField label="Klucz (feature_key)" size="small" value={editingFeat?.feature_key || ""}
            onChange={(e) => setEditingFeat({ ...editingFeat, feature_key: e.target.value })} />
          <TextField label="Nazwa wyświetlana" size="small" value={editingFeat?.display_name || ""}
            onChange={(e) => setEditingFeat({ ...editingFeat, display_name: e.target.value })} />
          <Select size="small" label="Kategoria" value={editingFeat?.category_id || ""}
            onChange={(e) => setEditingFeat({ ...editingFeat, category_id: Number(e.target.value) })}>
            {categories.map((c) => <MenuItem key={c.id} value={c.id}>{c.display_name}</MenuItem>)}
          </Select>
          <Select size="small" label="Typ cechy" value={editingFeat?.feature_type || "boolean"}
            onChange={(e) => setEditingFeat({ ...editingFeat, feature_type: e.target.value })}>
            <MenuItem value="boolean">boolean</MenuItem>
            <MenuItem value="numeric">numeric</MenuItem>
            <MenuItem value="text">text</MenuItem>
            <MenuItem value="enum">enum</MenuItem>
          </Select>
        <Select size="small" value={editingFeat?.vehicle_scope || "both"}
            onChange={(e) => setEditingFeat({ ...editingFeat, vehicle_scope: e.target.value })}>
            <MenuItem value="both">Oba (both)</MenuItem>
            <MenuItem value="commercial">Użytkowe (commercial)</MenuItem>
            <MenuItem value="passenger">Osobowe (passenger)</MenuItem>
          </Select>
          <Box sx={{ border: "1px solid #ccc", p: 1, borderRadius: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: "block" }}>Dedukowane dla typów zabudowy (zostaw puste dla wszystkich):</Typography>
            <Select size="small" multiple fullWidth value={editingFeat?.applicable_body_types || []}
              onChange={(e) => setEditingFeat({ ...editingFeat, applicable_body_types: typeof e.target.value === 'string' ? e.target.value.split(',') : e.target.value })}>
              <MenuItem value="SUV">SUV</MenuItem>
              <MenuItem value="Hatchback">Hatchback</MenuItem>
              <MenuItem value="Kombi">Kombi</MenuItem>
              <MenuItem value="Sedan">Sedan</MenuItem>
              <MenuItem value="Furgon">Furgon</MenuItem>
              <MenuItem value="Skrzynio​wy">Skrzynia</MenuItem>
              <MenuItem value="Chłodnia">Chłodnia</MenuItem>
              <MenuItem value="Kontener">Kontener</MenuItem>
              <MenuItem value="Izoterma">Izoterma</MenuItem>
              <MenuItem value="Platforma">Platforma</MenuItem>
              <MenuItem value="Wywrotka">Wywrotka</MenuItem>
            </Select>
          </Box>
          <TextField label="Sort order" size="small" type="number" value={editingFeat?.sort_order ?? 100}
            onChange={(e) => setEditingFeat({ ...editingFeat, sort_order: Number(e.target.value) })} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFeatDialog(false)}>Anuluj</Button>
          <Button variant="contained" onClick={saveFeat}>Zapisz</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

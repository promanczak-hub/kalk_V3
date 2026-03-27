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
  Tabs,
  Tab,
} from "@mui/material";
import { Edit, Trash2, Plus } from "lucide-react";
import { API_BASE_URL } from "../config/env";
import { apiClient } from "../lib/apiClient";

const BASE_URL = API_BASE_URL;

const VEHICLE_CLASSES = ["Osobowy", "Dostawczy"] as const;

interface BodyTypeItem {
  id?: number;
  name: string;
  vehicle_class: string;
  description?: string;
}

interface BodyTypeWRCorrectionItem {
  id?: number;
  samar_class_id: number | null;
  engine_type_id: number | null;
  brand_name: string;
  body_type_id: number | null;
  correction_percent: number;
  zabudowa_correction_percent: number;
}

function getClassColor(vc: string): "primary" | "warning" | "default" {
  if (vc === "Osobowy") return "primary";
  if (vc === "Dostawczy") return "warning";
  return "default";
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}
function CustomTabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

export default function BodyTypesCrudPanel() {
  const [tabIndex, setTabIndex] = useState(0);

  // States for Tab 0: Słownik Nadwozi
  const [data, setData] = useState<BodyTypeItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [formData, setFormData] = useState<BodyTypeItem>({
    name: "",
    vehicle_class: VEHICLE_CLASSES[0],
    description: "",
  });
  const [editingId, setEditingId] = useState<number | null>(null);

  // States for Tab 1: Korekty WR Nadwozi
  const [corrections, setCorrections] = useState<BodyTypeWRCorrectionItem[]>([]);
  const [loadingCorr, setLoadingCorr] = useState(false);
  const [modalCorrOpen, setModalCorrOpen] = useState(false);
  const [formCorrData, setFormCorrData] = useState<BodyTypeWRCorrectionItem>({
    samar_class_id: null,
    engine_type_id: null,
    brand_name: "",
    body_type_id: null,
    correction_percent: 0.0,
    zabudowa_correction_percent: 0.0,
  });
  const [editingCorrId, setEditingCorrId] = useState<number | null>(null);

  useEffect(() => {
    fetchData();
    fetchCorrections();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const resp = await apiClient.fetch(`${BASE_URL}/api/body-types`);
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

  const fetchCorrections = async () => {
    setLoadingCorr(true);
    try {
      const resp = await apiClient.fetch(`${BASE_URL}/api/body-type-wr-corrections`);
      if (resp.ok) {
        const json = await resp.json();
        if (Array.isArray(json)) setCorrections(json);
      }
    } catch (e) {
      console.error("Failed to load body type WR corrections:", e);
    } finally {
      setLoadingCorr(false);
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
      const resp = await apiClient.fetch(`${BASE_URL}/api/body-types`, {
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
      const resp = await apiClient.fetch(`${BASE_URL}/api/body-types/${id}`, {
        method: "DELETE",
      });
      if (resp.ok) fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  // Corr Handlers
  const handleCorrOpen = (item?: BodyTypeWRCorrectionItem) => {
    if (item) {
      setFormCorrData(item);
      setEditingCorrId(item.id || null);
    } else {
      setFormCorrData({
        samar_class_id: null,
        engine_type_id: null,
        brand_name: "",
        body_type_id: null,
        correction_percent: 0.0,
        zabudowa_correction_percent: 0.0,
      });
      setEditingCorrId(null);
    }
    setModalCorrOpen(true);
  };
  const handleCorrClose = () => setModalCorrOpen(false);

  const handleCorrSave = async () => {
    try {
      const resp = await apiClient.fetch(`${BASE_URL}/api/body-type-wr-corrections`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formCorrData),
      });
      if (resp.ok) {
        fetchCorrections();
        handleCorrClose();
      } else alert("Błąd zapisu korekty");
    } catch (e) {
      console.error(e);
      alert("Błąd komunikacji");
    }
  };

  const handleCorrDelete = async (id: number) => {
    if (!confirm("Na pewno usunąć tę korektę WR?")) return;
    try {
      const resp = await apiClient.fetch(`${BASE_URL}/api/body-type-wr-corrections/${id}`, {
        method: "DELETE",
      });
      if (resp.ok) fetchCorrections();
    } catch (e) {
      console.error(e);
    }
  };

  const grouped = VEHICLE_CLASSES.map((vc) => ({
    label: vc,
    items: data.filter((d) => d.vehicle_class === vc),
  }));

  return (
    <Box>
      <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Tabs value={tabIndex} onChange={(_, val) => setTabIndex(val)}>
          <Tab label="Słownik Nadwozi (Baza)" />
          <Tab label="Korekty WR Nadwozi / Zabudów (Monolity)" />
        </Tabs>
      </Box>

      {/* TAB 0: السلownik */}
      <CustomTabPanel value={tabIndex} index={0}>
        <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
          <Typography variant="h6">Słownik Typów Nadwozia</Typography>
          <Button variant="contained" startIcon={<Plus size={16} />} onClick={() => handleOpen()}>
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
                    <TableCell colSpan={4} sx={{ bgcolor: "rgba(0,0,0,0.04)", fontWeight: 700, fontSize: "0.8rem" }}>
                      {group.label === "Osobowy" ? "🚗" : "🚛"} {group.label} ({group.items.length})
                    </TableCell>
                  </TableRow>,
                  ...group.items.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell sx={{ fontWeight: 500, pl: 4 }}>{row.name}</TableCell>
                      <TableCell>
                        <Chip label={row.vehicle_class} size="small" color={getClassColor(row.vehicle_class)} variant="outlined" />
                      </TableCell>
                      <TableCell>{row.description || "—"}</TableCell>
                      <TableCell align="right">
                        <IconButton size="small" onClick={() => handleOpen(row)} color="primary"><Edit size={16} /></IconButton>
                        <IconButton size="small" color="error" onClick={() => row.id && handleDelete(row.id)}><Trash2 size={16} /></IconButton>
                      </TableCell>
                    </TableRow>
                  )),
                ])}
                {data.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} align="center" sx={{ py: 3, color: "text.secondary" }}>
                      Brak zdefiniowanych typów nadwozia. Dodaj pierwsze wpisy.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </CustomTabPanel>

      {/* TAB 1: Korekty WR */}
      <CustomTabPanel value={tabIndex} index={1}>
        <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
          <Box>
            <Typography variant="h6">Zarządzanie Korektami Nadwozi</Typography>
            <Typography variant="body2" color="text.secondary">
              Reguły nakładane na WR: Marka + Typ Nadwozia + Silnik (Nadwozia Osobowe) oraz Typ Zabudowy + Klasa SAMAR (Dostawcze i Zabudowy).
            </Typography>
          </Box>
          <Button variant="contained" startIcon={<Plus size={16} />} onClick={() => handleCorrOpen()}>
            Dodaj Korektę
          </Button>
        </Box>
        {loadingCorr ? (
          <CircularProgress />
        ) : (
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead sx={{ backgroundColor: "#f8fafc" }}>
                <TableRow>
                  <TableCell>Marka</TableCell>
                  <TableCell>Nadwozie ID</TableCell>
                  <TableCell>Silnik ID</TableCell>
                  <TableCell>Klasa SAMAR ID</TableCell>
                  <TableCell>Korekta Nadwozia [%]</TableCell>
                  <TableCell>Korekta Zabudowy [%]</TableCell>
                  <TableCell align="right">Akcje</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {corrections.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell sx={{ fontWeight: 500 }}>{row.brand_name || <Chip label="Wszystkie" size="small" />}</TableCell>
                    <TableCell>{row.body_type_id !== null ? row.body_type_id : <Chip label="Wszystkie" size="small" />}</TableCell>
                    <TableCell>{row.engine_type_id !== null ? row.engine_type_id : <Chip label="Wszystkie" size="small" />}</TableCell>
                    <TableCell>{row.samar_class_id !== null ? row.samar_class_id : <Chip label="Wszystkie" size="small" />}</TableCell>
                    <TableCell>{(row.correction_percent * 100).toFixed(2)}%</TableCell>
                    <TableCell>{(row.zabudowa_correction_percent * 100).toFixed(2)}%</TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => handleCorrOpen(row)} color="primary"><Edit size={16} /></IconButton>
                      <IconButton size="small" color="error" onClick={() => row.id && handleCorrDelete(row.id)}><Trash2 size={16} /></IconButton>
                    </TableCell>
                  </TableRow>
                ))}
                {corrections.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} align="center" sx={{ py: 3, color: "text.secondary" }}>
                      Brak zdefiniowanych korekt.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </CustomTabPanel>

      {/* DIALOG 0: Dictionary */}
      <Dialog open={modalOpen} onClose={handleClose} fullWidth maxWidth="sm">
        <DialogTitle>{editingId ? "Edytuj Typ Nadwozia" : "Nowy Typ Nadwozia"}</DialogTitle>
        <DialogContent dividers sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <TextField label="Nazwa (np. Hatchback, Furgon)" size="small" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} autoFocus />
          <TextField select label="Kategoria pojazdu" size="small" value={formData.vehicle_class} onChange={(e) => setFormData({ ...formData, vehicle_class: e.target.value })}>
            {VEHICLE_CLASSES.map((vc) => <MenuItem key={vc} value={vc}>{vc}</MenuItem>)}
          </TextField>
          <TextField label="Opis (opcjonalny)" size="small" multiline rows={2} value={formData.description || ""} onChange={(e) => setFormData({ ...formData, description: e.target.value })} />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Anuluj</Button>
          <Button variant="contained" onClick={handleSave} disabled={!formData.name || !formData.vehicle_class}>Zapisz</Button>
        </DialogActions>
      </Dialog>

      {/* DIALOG 1: Corrections */}
      <Dialog open={modalCorrOpen} onClose={handleCorrClose} fullWidth maxWidth="sm">
        <DialogTitle>{editingCorrId ? "Edytuj Korektę WR Nadwozia" : "Nowa Korekta WR Nadwozia"}</DialogTitle>
        <DialogContent dividers sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Typography variant="caption" color="error">Monolit Nadwozia/Zabudowy: Pozostaw puste aby reguła była ogólna (fallback).</Typography>
          <TextField label="Marka (Opcjonalnie)" size="small" value={formCorrData.brand_name} onChange={(e) => setFormCorrData({ ...formCorrData, brand_name: e.target.value })} />
          <TextField label="Typ Nadwozia ID (Opcjonalnie)" size="small" type="number" value={formCorrData.body_type_id || ""} onChange={(e) => setFormCorrData({ ...formCorrData, body_type_id: e.target.value ? parseInt(e.target.value) : null })} />
          <TextField label="Silnik ID (Opcjonalnie)" size="small" type="number" value={formCorrData.engine_type_id || ""} onChange={(e) => setFormCorrData({ ...formCorrData, engine_type_id: e.target.value ? parseInt(e.target.value) : null })} />
          <TextField label="Klasa SAMAR ID (Opcjonalnie, dla dostawczych)" size="small" type="number" value={formCorrData.samar_class_id || ""} onChange={(e) => setFormCorrData({ ...formCorrData, samar_class_id: e.target.value ? parseInt(e.target.value) : null })} />
          <TextField label="Korekta Nadwozia (ułamek np. 0.02 dla 2%)" size="small" type="number" inputProps={{ step: "0.001" }} value={formCorrData.correction_percent} onChange={(e) => setFormCorrData({ ...formCorrData, correction_percent: parseFloat(e.target.value) })} />
          <TextField label="Korekta Zabudowy (ułamek np. -0.01 dla -1%)" size="small" type="number" inputProps={{ step: "0.001" }} value={formCorrData.zabudowa_correction_percent} onChange={(e) => setFormCorrData({ ...formCorrData, zabudowa_correction_percent: parseFloat(e.target.value) })} />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCorrClose}>Anuluj</Button>
          <Button variant="contained" onClick={handleCorrSave}>Zapisz</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

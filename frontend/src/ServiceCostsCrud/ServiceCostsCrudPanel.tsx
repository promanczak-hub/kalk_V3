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
  Tabs,
  Tab,
} from "@mui/material";
import { Edit, Trash2, Plus, AlertCircle } from "lucide-react";
import { apiClient } from '../lib/apiClient';

interface SamarClass {
  id: number;
  name: string;
  example_models?: string;
}

interface SamarClassServiceRate {
  id?: string;
  samar_class_id: number;
  mileage_up_to: number;
  cost_aso_per_km: number;
  cost_non_aso_per_km: number;
}

interface ServiceMultiplier {
  id?: string;
  name_normalized: string;
  multiplier: number;
}

function BaseRatesTable({ samarClasses }: { samarClasses: SamarClass[] }) {
  const [data, setData] = useState<SamarClassServiceRate[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  
  const [formData, setFormData] = useState<SamarClassServiceRate>({
    samar_class_id: 0,
    mileage_up_to: 20000,
    cost_aso_per_km: 0.1,
    cost_non_aso_per_km: 0.08,
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const resp = await apiClient.fetch(`/api/samar-class-service-rates`);
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

  const getClassName = (id: number) => {
    const found = samarClasses.find((c) => c.id === id);
    return found ? found.name : `Klasa ID: ${id}`;
  };

  const getExampleModels = (id: number) => {
    const found = samarClasses.find((c) => c.id === id);
    return found?.example_models || "Brak danych";
  };

  const handleOpen = (item?: SamarClassServiceRate) => {
    if (item) {
      setFormData(item);
    } else {
      const initialClassId = samarClasses.length > 0 ? samarClasses[0].id : 1;
      setFormData({
        samar_class_id: initialClassId,
        mileage_up_to: 20000,
        cost_aso_per_km: 0.15,
        cost_non_aso_per_km: 0.08,
      });
    }
    setModalOpen(true);
  };

  const handleClose = () => setModalOpen(false);

  const handleSave = async () => {
    try {
      const resp = await apiClient.fetch(`/api/samar-class-service-rates/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // The API expects a list for bulk upsert
        body: JSON.stringify([formData]),
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

  const handleDelete = async (id: string) => {
    if (!confirm("Na pewno usunąć?")) return;
    try {
      const resp = await apiClient.fetch(`/api/samar-class-service-rates/${id}`, {
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
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="subtitle1" fontWeight="bold">Stawki Bazowe (wg progu przebiegu)</Typography>
        <Button
          variant="contained"
          startIcon={<Plus size={16} />}
          onClick={() => handleOpen()}
          disabled={loading}
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
                <TableCell>Przykładowe Modele</TableCell>
                <TableCell align="right">Próg Przebiegu (do km)</TableCell>
                <TableCell align="right">Koszt ASO za km (Netto)</TableCell>
                <TableCell align="right">Koszt Non-ASO za km (Netto)</TableCell>
                <TableCell align="right">Akcje</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{getClassName(row.samar_class_id)}</TableCell>
                  <TableCell title={getExampleModels(row.samar_class_id)} sx={{ maxWidth: 250, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {getExampleModels(row.samar_class_id)}
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>{row.mileage_up_to.toLocaleString()} km</TableCell>
                  <TableCell align="right">{row.cost_aso_per_km} zł</TableCell>
                  <TableCell align="right">{row.cost_non_aso_per_km} zł</TableCell>
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
                  <TableCell colSpan={6} align="center" sx={{ py: 3, color: "text.secondary" }}>
                    Brak stawek bazowych. Dodaj pierwsze wpisy.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={modalOpen} onClose={handleClose} fullWidth maxWidth="sm">
        <DialogTitle>{formData.id ? "Edytuj Stawkę" : "Nowa Stawka Bazowa"}</DialogTitle>
        <DialogContent dividers sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <TextField
            select
            label="Klasa SAMAR"
            size="small"
            value={formData.samar_class_id}
            onChange={(e) => setFormData({ ...formData, samar_class_id: parseInt(e.target.value) })}
          >
            {(samarClasses.length > 0 ? samarClasses : [{id: 1, name: "Klasa A (1)"}]).map((c) => (
              <MenuItem key={c.id} value={c.id}>
                {c.name}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            label="Próg Przebiegu (do km)"
            type="number"
            size="small"
            fullWidth
            inputProps={{ step: 1000 }}
            value={formData.mileage_up_to}
            onChange={(e) => setFormData({ ...formData, mileage_up_to: parseInt(e.target.value) || 0 })}
            helperText="Przykład: 20000, 40000, 1000000 (jako fallback)"
          />

          <Box sx={{ display: "flex", gap: 2 }}>
            <TextField
              label="Koszt ASO / 1km (PLN)"
              type="number"
              size="small"
              fullWidth
              inputProps={{ step: 0.001 }}
              value={formData.cost_aso_per_km}
              onChange={(e) => setFormData({ ...formData, cost_aso_per_km: parseFloat(e.target.value) })}
            />
             <TextField
              label="Koszt Non-ASO / 1km (PLN)"
              type="number"
              size="small"
              fullWidth
              inputProps={{ step: 0.001 }}
              value={formData.cost_non_aso_per_km}
              onChange={(e) => setFormData({ ...formData, cost_non_aso_per_km: parseFloat(e.target.value) })}
            />
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

function MultipliersTable({ type, labelName }: { type: string, labelName: string }) {
  const [data, setData] = useState<ServiceMultiplier[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  
  const [formData, setFormData] = useState<ServiceMultiplier>({
    name_normalized: "",
    multiplier: 1.0,
  });

  useEffect(() => {
    fetchData();
  }, [type]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const resp = await apiClient.fetch(`/api/service-multipliers/${type}`);
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

  const handleOpen = (item?: ServiceMultiplier) => {
    if (item) {
      setFormData(item);
    } else {
      setFormData({
        name_normalized: "",
        multiplier: 1.0,
      });
    }
    setModalOpen(true);
  };

  const handleClose = () => setModalOpen(false);

  const handleSave = async () => {
    if (!formData.name_normalized.trim()) return;
    try {
      const resp = await apiClient.fetch(`/api/service-multipliers/${type}`, {
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

  const handleDelete = async (id: string) => {
    if (!confirm("Na pewno usunąć?")) return;
    try {
      const resp = await apiClient.fetch(`/api/service-multipliers/${type}/${id}`, {
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
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="subtitle1" fontWeight="bold">Mnożniki Systemowe: {labelName}</Typography>
        <Button
          variant="contained"
          startIcon={<Plus size={16} />}
          onClick={() => handleOpen()}
          disabled={loading}
        >
          Dodaj Mnożnik
        </Button>
      </Box>

      {loading ? (
        <CircularProgress />
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead sx={{ backgroundColor: "#f8fafc" }}>
              <TableRow>
                <TableCell>Nazwa ({labelName})</TableCell>
                <TableCell align="right">Mnożnik (np. 1.0)</TableCell>
                <TableCell align="right">Akcje</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.map((row) => (
                <TableRow key={row.id}>
                  <TableCell sx={{ fontWeight: 'medium' }}>{row.name_normalized}</TableCell>
                  <TableCell align="right">
                    <Box component="span" sx={{ 
                      px: 1, py: 0.5, borderRadius: 1, 
                      bgcolor: row.multiplier === 1 ? 'transparent' : (row.multiplier > 1 ? 'error.light' : 'success.light'),
                      color: row.multiplier === 1 ? 'inherit' : (row.multiplier > 1 ? 'error.dark' : 'success.dark'),
                      fontWeight: 'bold'
                    }}>
                      x{row.multiplier.toFixed(4)}
                    </Box>
                  </TableCell>
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
                  <TableCell colSpan={3} align="center" sx={{ py: 3, color: "text.secondary" }}>
                    Brak ustawionych mnożników. Domyślnie system stosuje x1.0 w przypadku braku wpisu.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={modalOpen} onClose={handleClose} fullWidth maxWidth="sm">
        <DialogTitle>{formData.id ? "Edytuj Mnożnik" : "Nowy Mnożnik"}</DialogTitle>
        <DialogContent dividers sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <TextField
            label={`Nazwa znormalizowana (${labelName})`}
            size="small"
            fullWidth
            value={formData.name_normalized}
            onChange={(e) => setFormData({ ...formData, name_normalized: e.target.value.toUpperCase() })}
            helperText="Zapisane zostanie wielkimi literami. Np. 'BENZYNA', 'HYBRYDA', 'PORSCHE'."
          />
          <TextField
            label="Wartość Mnożnika"
            type="number"
            size="small"
            fullWidth
            inputProps={{ step: 0.01 }}
            value={formData.multiplier}
            onChange={(e) => setFormData({ ...formData, multiplier: parseFloat(e.target.value) || 1.0 })}
            helperText="Wartość 1.0 oznacza brak wpływu (neutral). 1.15 to +15% do ceny bazowej."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Anuluj</Button>
          <Button variant="contained" onClick={handleSave} disabled={!formData.name_normalized.trim()}>
            Zapisz
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default function ServiceCostsCrudPanel() {
  const [samarClasses, setSamarClasses] = useState<SamarClass[]>([]);
  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    fetchDependencies();
  }, []);

  const fetchDependencies = async () => {
    try {
      const classesRes = await apiClient.fetch(`/api/samar-classes`).catch(() => null);
      if (classesRes?.ok) {
        setSamarClasses(await classesRes.json());
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h6">Koszty Serwisowe V3</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
          <AlertCircle size={14} />
          W nowej wersji (V3) klasyczny zestaw Silnik + Moc został zastąpiony mechanizmem macierzowymi (Stawka bazy * Mnożniki wg wyposażenia).
        </Typography>
      </Box>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, val) => setActiveTab(val)} variant="scrollable" scrollButtons="auto">
          <Tab label="Stawki Bazowe (Krok przebiegu)" />
          <Tab label="Mnożniki: Marka" />
          <Tab label="Mnożniki: Paliwo" />
          <Tab label="Mnożniki: Napęd" />
          <Tab label="Mnożniki: Skrzynia Biegów" />
        </Tabs>
      </Paper>

      <Box>
        {activeTab === 0 && <BaseRatesTable samarClasses={samarClasses} />}
        {activeTab === 1 && <MultipliersTable type="brand" labelName="Marka Pojazdu" />}
        {activeTab === 2 && <MultipliersTable type="fuel" labelName="Rodzaj Paliwa" />}
        {activeTab === 3 && <MultipliersTable type="drive" labelName="Rodzaj Napędu" />}
        {activeTab === 4 && <MultipliersTable type="gearbox" labelName="Skrzynia Biegów" />}
      </Box>
    </Box>
  );
}

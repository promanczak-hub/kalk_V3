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
import { Edit, Trash2, Plus, Download, Upload } from "lucide-react";
import { useRef } from "react";

interface SamarClass {
  id: number;
  name: string;
  example_models?: string;
}

interface EngineType {
  id: number;
  name: string;
  category: string;
}

interface SamarServiceCost {
  id?: string;
  samar_class_id: number;
  engine_type_id: number;
  power_band: string;
  cost_aso_per_km: number;
  cost_non_aso_per_km: number;
}

const POWER_BANDS = [
  { value: "LOW", label: "LOW (do 130 KM)" },
  { value: "MID", label: "MID (131 - 200 KM)" },
  { value: "HIGH", label: "HIGH (201 KM i więcej)" },
];

export default function ServiceCostsCrudPanel() {
  const [data, setData] = useState<SamarServiceCost[]>([]);
  const [samarClasses, setSamarClasses] = useState<SamarClass[]>([]);
  const [engines, setEngines] = useState<EngineType[]>([]);
  const [loading, setLoading] = useState(false);
  
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [formData, setFormData] = useState<SamarServiceCost>({
    samar_class_id: 0,
    engine_type_id: 0,
    power_band: "MID",
    cost_aso_per_km: 0.1,
    cost_non_aso_per_km: 0.08,
  });

  useEffect(() => {
    fetchDependencies();
    fetchData();
  }, []);

  const fetchDependencies = async () => {
    try {
      const [enginesRes, classesRes] = await Promise.all([
        fetch(`http://127.0.0.1:8000/api/engines`),
        // Endpoint dla klas SAMAR jest z RV lub z backendu, jeśli nie ma, omijamy błąd
        // Jeśli posiadamy classes z RV:
        fetch(`http://127.0.0.1:8000/api/samar-classes`).catch(() => null)
      ]);
      
      if (enginesRes?.ok) {
        setEngines(await enginesRes.json());
      }
      
      if (classesRes?.ok) {
        setSamarClasses(await classesRes.json());
      } else {
        // Fallback: pobieranie połączone do Supabase JS w razie braku routera (wymaga klienta)
        // Jeśli nie korzystamy bezpośrednio z supabase, pusta tablica użyje mocków
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`http://127.0.0.1:8000/api/samar-service-costs`);
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

  const getEngineName = (id: number) => {
    const found = engines.find((e) => e.id === id);
    return found ? `${found.name} (${found.category})` : `Silnik ID: ${id}`;
  };

  const getPowerBandLabel = (val: string) => {
    const found = POWER_BANDS.find(p => p.value === val);
    return found ? found.label : val;
  };

  const getAllowedPowerBands = (classId: number) => {
    const className = getClassName(classId).toUpperCase();
    
    let allowed = ["MID", "HIGH"];
    
    if (className.includes("MINI")) {
      allowed = ["LOW"];
    } else if (
      className.includes("MAŁE") || 
      className.includes("B-SUV") || 
      className.includes("DOSTAWCZE") || 
      className.includes("PICK-UP")
    ) {
      allowed = ["LOW", "MID"];
    } else if (
      className.includes("NIŻSZA ŚREDNIA") || 
      className.includes("C-SUV") || 
      className.includes("ŚREDNIA") || 
      className.includes("D-SUV")
    ) {
      allowed = ["LOW", "MID", "HIGH"];
    } else if (
      className.includes("SPORTOWE") || 
      className.includes("KABRIOLETY") || 
      className.includes("LUKSUSOWE") || 
      className.includes("F-SUV")
    ) {
      allowed = ["HIGH"];
    } else if (
      className.includes("WYŻSZA") || 
      className.includes("E-SUV")
    ) {
      allowed = ["MID", "HIGH"];
    }
    
    return POWER_BANDS.filter(p => allowed.includes(p.value));
  };

  const handleOpen = (item?: SamarServiceCost) => {
    if (item) {
      setFormData(item);
      setEditingId(item.id || null);
    } else {
      const initialClassId = samarClasses.length > 0 ? samarClasses[0].id : 1;
      const allowedBands = getAllowedPowerBands(initialClassId);
      
      setFormData({
        samar_class_id: initialClassId,
        engine_type_id: engines.length > 0 ? engines[0].id : 1,
        power_band: allowedBands.length > 0 ? allowedBands[0].value : "MID",
        cost_aso_per_km: 0.15,
        cost_non_aso_per_km: 0.08,
      });
      setEditingId(null);
    }
    setModalOpen(true);
  };

  const handleClose = () => setModalOpen(false);

  const handleSave = async () => {
    try {
      const resp = await fetch(`http://127.0.0.1:8000/api/samar-service-costs`, {
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
      const resp = await fetch(`http://127.0.0.1:8000/api/samar-service-costs/${id}`, {
        method: "DELETE",
      });
      if (resp.ok) {
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleExportExcel = async () => {
    setExporting(true);
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/samar-service-costs/export`);
      if (!response.ok) throw new Error("Błąd przy eksporcie");
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "koszty_serwisowe_eksport.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      console.error(e);
      alert("Wystąpił błąd podczas eksportowania pliku Excel.");
    } finally {
      setExporting(false);
    }
  };

  const handleImportExcel = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setImporting(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`http://127.0.0.1:8000/api/samar-service-costs/import`, {
        method: "POST",
        body: formData,
      });
      
      if (response.ok) {
        const result = await response.json();
        alert(result.message);
        fetchData();
      } else {
        const err = await response.json();
        alert(`Błąd importu: ${err.detail || 'Nieznany błąd'}`);
      }
    } catch (e) {
      console.error(e);
      alert("Wystąpił błąd komunikacji z serwerem podczas importu.");
    } finally {
      setImporting(false);
      // reset file input
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h6">Koszty Serwisowe (ASO / Non-ASO)</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={exporting ? <CircularProgress size={16} /> : <Download size={16} />}
            onClick={handleExportExcel}
            disabled={exporting || importing}
          >
            Eksportuj do Excel
          </Button>
          
          <input
            type="file"
            accept=".xlsx"
            style={{ display: "none" }}
            ref={fileInputRef}
            onChange={handleImportExcel}
          />
          <Button
            variant="outlined"
            color="secondary"
            startIcon={importing ? <CircularProgress size={16} /> : <Upload size={16} />}
            onClick={() => fileInputRef.current?.click()}
            disabled={exporting || importing}
          >
            Importuj z Excela
          </Button>

          <Button
            variant="contained"
            startIcon={<Plus size={16} />}
            onClick={() => handleOpen()}
            disabled={exporting || importing}
          >
            Dodaj Koszt
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
                <TableCell>Klasa SAMAR</TableCell>
                <TableCell>Przykładowe Modele</TableCell>
                <TableCell>Napęd (Silnik)</TableCell>
                <TableCell>Przedział Mocy</TableCell>
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
                  <TableCell>{getEngineName(row.engine_type_id)}</TableCell>
                  <TableCell>{getPowerBandLabel(row.power_band)}</TableCell>
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
                    Brak macierzy kosztów. Dodaj pierwsze wpisy.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={modalOpen} onClose={handleClose} fullWidth maxWidth="sm">
        <DialogTitle>{editingId ? "Edytuj Koszt Serwisowy" : "Nowy Koszt Serwisowy"}</DialogTitle>
        <DialogContent dividers sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <TextField
            select
            label="Klasa SAMAR"
            size="small"
            value={formData.samar_class_id}
            onChange={(e) => {
              const newClassId = parseInt(e.target.value);
              const allowedBands = getAllowedPowerBands(newClassId);
              const isCurrentBandAllowed = allowedBands.some(b => b.value === formData.power_band);
              
              setFormData({ 
                ...formData, 
                samar_class_id: newClassId,
                power_band: isCurrentBandAllowed ? formData.power_band : (allowedBands[0]?.value || "MID")
              });
            }}
          >
           {(samarClasses.length > 0 ? samarClasses : [{id: 1, name: "Klasa A (1)"}, {id: 2, name: "Klasa B (2)"}, {id: 3, name: "Klasa C (3)"}]).map((c) => (
              <MenuItem key={c.id} value={c.id}>
                {c.name}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            select
            label="Napęd silnika"
            size="small"
            value={formData.engine_type_id}
            onChange={(e) => setFormData({ ...formData, engine_type_id: parseInt(e.target.value) })}
          >
            {engines.map((e) => (
              <MenuItem key={e.id} value={e.id}>
                {e.name}
              </MenuItem>
            ))}
            {engines.length === 0 && <MenuItem value={0}>Ładowanie...</MenuItem>}
          </TextField>

          <TextField
            select
            label="Przedział mocy"
            size="small"
            value={formData.power_band}
            onChange={(e) => setFormData({ ...formData, power_band: e.target.value })}
          >
            {getAllowedPowerBands(formData.samar_class_id).map((p) => (
               <MenuItem key={p.value} value={p.value}>
                 {p.label}
               </MenuItem>
            ))}
          </TextField>

          <Box sx={{ display: "flex", gap: 2 }}>
            <TextField
              label="Koszt ASO / 1km (PLN)"
              type="number"
              size="small"
              fullWidth
              inputProps={{ step: 0.01 }}
              value={formData.cost_aso_per_km}
              onChange={(e) => setFormData({ ...formData, cost_aso_per_km: parseFloat(e.target.value) })}
            />
             <TextField
              label="Koszt Non-ASO / 1km (PLN)"
              type="number"
              size="small"
              fullWidth
              inputProps={{ step: 0.01 }}
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

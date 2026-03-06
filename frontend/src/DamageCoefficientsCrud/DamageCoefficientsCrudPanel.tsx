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
  alpha,
} from "@mui/material";
import { Edit, Trash2, Plus } from "lucide-react";

const BASE_URL = "http://127.0.0.1:8000";

interface SamarClass {
  id: number;
  name: string;
}

interface DamageCoefficient {
  id?: number;
  klasa_wr_id: number | null;
  wsp_sredni_przebieg: number;
  wsp_wartosc_szkody: number;
}

export default function DamageCoefficientsCrudPanel() {
  const [data, setData] = useState<DamageCoefficient[]>([]);
  const [samarClasses, setSamarClasses] = useState<SamarClass[]>([]);
  const [loading, setLoading] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const [formData, setFormData] = useState<DamageCoefficient>({
    klasa_wr_id: null,
    wsp_sredni_przebieg: 1.0,
    wsp_wartosc_szkody: 1.0,
  });

  useEffect(() => {
    fetchDependencies();
    fetchData();
  }, []);

  const fetchDependencies = async () => {
    try {
      const res = await fetch(`${BASE_URL}/api/samar-classes`).catch(
        () => null,
      );
      if (res?.ok) {
        setSamarClasses(await res.json());
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const resp = await fetch(
        `${BASE_URL}/api/samar-rv/insurance-coefficients`,
      );
      if (resp.ok) {
        const raw = await resp.json();
        setData(Array.isArray(raw) ? raw : []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const getClassName = (klasaId: number | null): string => {
    if (klasaId === null) return "— Domyślna (null) —";
    const found = samarClasses.find((c) => c.id === klasaId);
    return found ? found.name : `Klasa ID: ${klasaId}`;
  };

  const handleOpen = (item?: DamageCoefficient) => {
    if (item) {
      setFormData({ ...item });
      setEditingId(item.id ?? null);
    } else {
      setFormData({
        klasa_wr_id: samarClasses.length > 0 ? samarClasses[0].id : null,
        wsp_sredni_przebieg: 1.0,
        wsp_wartosc_szkody: 1.0,
      });
      setEditingId(null);
    }
    setModalOpen(true);
  };

  const handleClose = () => setModalOpen(false);

  const handleSave = async () => {
    try {
      const payload = { ...formData };

      const resp = await fetch(
        `${BASE_URL}/api/samar-rv/insurance-coefficients`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
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

  const handleDelete = async (id: number) => {
    if (!confirm("Na pewno usunąć?")) return;
    try {
      const resp = await fetch(
        `${BASE_URL}/api/samar-rv/insurance-coefficients/${id}`,
        { method: "DELETE" },
      );
      if (resp.ok) fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  const usedClassIds = new Set(data.map((d) => d.klasa_wr_id));

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h6">
          💥 Współczynniki Szkodowe (per klasa SAMAR)
        </Typography>
        <Button
          variant="contained"
          startIcon={<Plus size={16} />}
          onClick={() => handleOpen()}
        >
          Dodaj Współczynnik
        </Button>
      </Box>

      {loading ? (
        <CircularProgress />
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead
              sx={{
                backgroundColor: (t) =>
                  t.palette.mode === "dark"
                    ? alpha("#e65100", 0.15)
                    : "#fff3e0",
              }}
            >
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>Klasa SAMAR</TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>
                  Wsp. Średni Przebieg
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>
                  Wsp. Wartość Szkody
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>
                  Mnożnik łączny
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>
                  Akcje
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>
                    <Chip
                      label={getClassName(row.klasa_wr_id)}
                      size="small"
                      color="warning"
                      variant="outlined"
                      sx={{ fontWeight: 600 }}
                    />
                  </TableCell>
                  <TableCell
                    align="right"
                    sx={{ fontFamily: "monospace", fontWeight: 600 }}
                  >
                    {Number(row.wsp_sredni_przebieg).toFixed(4)}
                  </TableCell>
                  <TableCell
                    align="right"
                    sx={{ fontFamily: "monospace", fontWeight: 600 }}
                  >
                    {Number(row.wsp_wartosc_szkody).toFixed(4)}
                  </TableCell>
                  <TableCell
                    align="right"
                    sx={{
                      fontFamily: "monospace",
                      color: "text.secondary",
                    }}
                  >
                    ×{" "}
                    {(
                      Number(row.wsp_sredni_przebieg) *
                      Number(row.wsp_wartosc_szkody)
                    ).toFixed(4)}
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
                    colSpan={5}
                    align="center"
                    sx={{ py: 3, color: "text.secondary" }}
                  >
                    Brak współczynników szkodowych. Dodaj wpisy lub uruchom
                    seed.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Edit/Add Dialog */}
      <Dialog open={modalOpen} onClose={handleClose} fullWidth maxWidth="sm">
        <DialogTitle>
          {editingId
            ? "Edytuj Współczynnik Szkodowy"
            : "Nowy Współczynnik Szkodowy"}
        </DialogTitle>
        <DialogContent
          dividers
          sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 2 }}
        >
          <TextField
            select
            label="Klasa SAMAR"
            size="small"
            value={formData.klasa_wr_id ?? "null"}
            onChange={(e) => {
              const val = e.target.value;
              setFormData({
                ...formData,
                klasa_wr_id: val === "null" ? null : parseInt(val),
              });
            }}
          >
            <MenuItem value="null">— Domyślna (null) —</MenuItem>
            {samarClasses.map((c) => (
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
              label="Wsp. Średni Przebieg"
              type="number"
              size="small"
              fullWidth
              inputProps={{ step: 0.01, min: 0 }}
              value={formData.wsp_sredni_przebieg}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  wsp_sredni_przebieg: parseFloat(e.target.value) || 0,
                })
              }
            />
            <TextField
              label="Wsp. Wartość Szkody"
              type="number"
              size="small"
              fullWidth
              inputProps={{ step: 0.01, min: 0 }}
              value={formData.wsp_wartosc_szkody}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  wsp_wartosc_szkody: parseFloat(e.target.value) || 0,
                })
              }
            />
          </Box>

          {formData.wsp_sredni_przebieg > 0 &&
            formData.wsp_wartosc_szkody > 0 && (
              <Typography
                variant="body2"
                sx={{
                  color: "text.secondary",
                  p: 1.5,
                  borderRadius: 1,
                  bgcolor: (t) =>
                    t.palette.mode === "dark"
                      ? alpha("#e65100", 0.08)
                      : "#fff8e1",
                }}
              >
                Mnożnik łączny:{" "}
                <strong>
                  ×{" "}
                  {(
                    formData.wsp_sredni_przebieg * formData.wsp_wartosc_szkody
                  ).toFixed(4)}
                </strong>{" "}
                | Formuła: średnia_szkoda × (km_total / km_ref ×{" "}
                {formData.wsp_sredni_przebieg.toFixed(2)} ×{" "}
                {formData.wsp_wartosc_szkody.toFixed(2)})
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

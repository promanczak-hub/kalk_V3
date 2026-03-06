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

interface KlasaWr {
  id: number;
  nazwa: string;
}

interface InsuranceRate {
  id?: number;
  KolejnyRok: number;
  StawkaBazowaAC: number;
  SkladkaOC: number;
  KlasaId: number | null;
}

export default function InsuranceRatesCrudPanel() {
  const [data, setData] = useState<InsuranceRate[]>([]);
  const [klasaWrList, setKlasaWrList] = useState<KlasaWr[]>([]);
  const [loading, setLoading] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const [formData, setFormData] = useState<InsuranceRate>({
    KolejnyRok: 1,
    StawkaBazowaAC: 0,
    SkladkaOC: 0,
    KlasaId: null,
  });

  useEffect(() => {
    fetchDependencies();
    fetchData();
  }, []);

  const fetchDependencies = async () => {
    try {
      const res = await fetch(`${BASE_URL}/api/samar-rv/classes`).catch(
        () => null,
      );
      if (res?.ok) {
        setKlasaWrList(await res.json());
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${BASE_URL}/api/samar-rv/insurance-rates`);
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
    const found = klasaWrList.find((c) => c.id === klasaId);
    return found ? found.nazwa : `Klasa ID: ${klasaId}`;
  };

  const handleOpen = (item?: InsuranceRate) => {
    if (item) {
      setFormData({ ...item });
      setEditingId(item.id ?? null);
    } else {
      setFormData({
        KolejnyRok: 1,
        StawkaBazowaAC: 0,
        SkladkaOC: 0,
        KlasaId: klasaWrList.length > 0 ? klasaWrList[0].id : null,
      });
      setEditingId(null);
    }
    setModalOpen(true);
  };

  const handleClose = () => setModalOpen(false);

  const handleSave = async () => {
    try {
      const payload = { ...formData };

      const resp = await fetch(`${BASE_URL}/api/samar-rv/insurance-rates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
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
    if (!confirm("Na pewno usunąć?")) return;
    try {
      const resp = await fetch(
        `${BASE_URL}/api/samar-rv/insurance-rates/${id}`,
        { method: "DELETE" },
      );
      if (resp.ok) fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  /* Group data by KlasaId for nicer display */
  const grouped: Record<string, InsuranceRate[]> = {};
  data.forEach((row) => {
    const key = row.KlasaId === null ? "null" : String(row.KlasaId);
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(row);
  });

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h6">
          🛡️ Stawki Ubezpieczeniowe AC / OC (per rok per klasa)
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
            <TableHead
              sx={{
                backgroundColor: (t) =>
                  t.palette.mode === "dark"
                    ? alpha("#1565c0", 0.15)
                    : "#e3f2fd",
              }}
            >
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>Klasa SAMAR</TableCell>
                <TableCell align="center" sx={{ fontWeight: 700 }}>
                  Rok
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>
                  Stawka Bazowa AC (%)
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>
                  Składka OC (PLN/rok)
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>
                  Akcje
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.entries(grouped).map(([klasaKey, rows]) => {
                const klasaId =
                  klasaKey === "null" ? null : parseInt(klasaKey);
                const klasaName = getClassName(klasaId);
                return rows
                  .sort((a, b) => a.KolejnyRok - b.KolejnyRok)
                  .map((row, idx) => (
                    <TableRow
                      key={row.id}
                      sx={{
                        borderTop:
                          idx === 0 ? "2px solid" : undefined,
                        borderTopColor:
                          idx === 0 ? "divider" : undefined,
                      }}
                    >
                      <TableCell sx={{ fontWeight: idx === 0 ? 600 : 400 }}>
                        {idx === 0 ? (
                          <Chip
                            label={klasaName}
                            size="small"
                            color="primary"
                            variant="outlined"
                            sx={{ fontWeight: 600 }}
                          />
                        ) : (
                          ""
                        )}
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={`Rok ${row.KolejnyRok}`}
                          size="small"
                          sx={{ fontSize: "0.75rem" }}
                        />
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{ fontFamily: "monospace", fontWeight: 600 }}
                      >
                        {(row.StawkaBazowaAC * 100).toFixed(4)}%
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{ fontFamily: "monospace" }}
                      >
                        {Number(row.SkladkaOC).toFixed(2)} zł
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
                  ));
              })}
              {data.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={5}
                    align="center"
                    sx={{ py: 3, color: "text.secondary" }}
                  >
                    Brak stawek ubezpieczeniowych. Dodaj wpisy lub uruchom seed.
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
            ? "Edytuj Stawkę Ubezpieczeniową"
            : "Nowa Stawka Ubezpieczeniowa"}
        </DialogTitle>
        <DialogContent
          dividers
          sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 2 }}
        >
          <TextField
            select
            label="Klasa SAMAR"
            size="small"
            value={formData.KlasaId ?? "null"}
            onChange={(e) => {
              const val = e.target.value;
              setFormData({
                ...formData,
                KlasaId: val === "null" ? null : parseInt(val),
              });
            }}
          >
            <MenuItem value="null">— Domyślna (null) —</MenuItem>
            {klasaWrList.map((c) => (
              <MenuItem key={c.id} value={c.id}>
                {c.nazwa}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            label="Kolejny Rok (1-7)"
            type="number"
            size="small"
            inputProps={{ min: 1, max: 7 }}
            value={formData.KolejnyRok}
            onChange={(e) =>
              setFormData({
                ...formData,
                KolejnyRok: parseInt(e.target.value) || 1,
              })
            }
          />

          <Box sx={{ display: "flex", gap: 2 }}>
            <TextField
              label="Stawka Bazowa AC (ułamek, np. 0.035)"
              type="number"
              size="small"
              fullWidth
              inputProps={{ step: 0.001, min: 0, max: 1 }}
              value={formData.StawkaBazowaAC}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  StawkaBazowaAC: parseFloat(e.target.value) || 0,
                })
              }
            />
            <TextField
              label="Składka OC (PLN/rok)"
              type="number"
              size="small"
              fullWidth
              inputProps={{ step: 10, min: 0 }}
              value={formData.SkladkaOC}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  SkladkaOC: parseFloat(e.target.value) || 0,
                })
              }
            />
          </Box>

          {formData.StawkaBazowaAC > 0 && (
            <Typography
              variant="body2"
              sx={{
                color: "text.secondary",
                p: 1.5,
                borderRadius: 1,
                bgcolor: (t) =>
                  t.palette.mode === "dark"
                    ? alpha("#1565c0", 0.08)
                    : "#f0f4ff",
              }}
            >
              Stawka AC:{" "}
              <strong>{(formData.StawkaBazowaAC * 100).toFixed(4)}%</strong> |
              Np. dla auta 100k netto: AC ≈{" "}
              <strong>
                {(formData.StawkaBazowaAC * 100000).toFixed(0)} PLN/rok
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

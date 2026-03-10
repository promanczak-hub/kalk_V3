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
  TextField,
  Chip,
  Snackbar,
  Alert,
  CircularProgress,
  alpha,
  useTheme,
} from "@mui/material";
import { Save } from "lucide-react";

const BASE_URL = import.meta.env.VITE_API_URL || "";

interface PaintType {
  id: number;
  name: string;
  wr_correction: number;
}

export default function PaintCorrectionCrudPanel() {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";
  const accent = "#ab47bc"; // purple for paint

  const [types, setTypes] = useState<PaintType[]>([]);
  const [edited, setEdited] = useState<Map<number, number>>(new Map());
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error";
  }>({ open: false, message: "", severity: "success" });

  const fetchTypes = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${BASE_URL}/api/paint-types`);
      if (resp.ok) {
        const data = await resp.json();
        setTypes(Array.isArray(data) ? data : []);
        setEdited(new Map());
      }
    } catch (e) {
      console.error("Failed to load paint types", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTypes();
  }, []);

  const getValue = (id: number): number => {
    return edited.has(id)
      ? edited.get(id)!
      : types.find((t) => t.id === id)?.wr_correction ?? 0;
  };

  const handleChange = (id: number, rawValue: string) => {
    const pct = parseFloat(rawValue);
    if (isNaN(pct)) return;
    setEdited((prev) => new Map(prev).set(id, pct / 100));
  };

  const handleSave = async () => {
    if (edited.size === 0) return;
    setSaving(true);
    try {
      const payload = Array.from(edited.entries()).map(([id, wr_correction]) => ({
        id,
        wr_correction,
      }));
      const resp = await fetch(`${BASE_URL}/api/paint-types/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error("Save failed");
      setSnackbar({ open: true, message: "Zapisano korekty lakieru", severity: "success" });
      await fetchTypes();
    } catch (e) {
      console.error(e);
      setSnackbar({ open: true, message: "Błąd zapisu", severity: "error" });
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = edited.size > 0;

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
        <Typography sx={{ fontWeight: 700, fontSize: "1rem", color: accent }}>
          🎨 Korekta WR za typ lakieru
        </Typography>
        <Button
          variant="contained"
          startIcon={saving ? <CircularProgress size={16} /> : <Save size={16} />}
          onClick={handleSave}
          disabled={!hasChanges || saving}
          sx={{ fontWeight: 600 }}
        >
          Zapisz zmiany
        </Button>
      </Box>

      <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mb: 2 }}>
        Korekta WR stosowana do ceny bazowej netto. Np. −1% = lakier niemetalik obniża WR o 1% ceny
        bazowej.
      </Typography>

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer
          component={Paper}
          elevation={0}
          sx={{
            borderRadius: 2,
            border: `1px solid ${alpha(accent, 0.3)}`,
          }}
        >
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: alpha(accent, isDark ? 0.1 : 0.04) }}>
                <TableCell sx={{ fontWeight: 700, width: 50 }}>ID</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Typ lakieru</TableCell>
                <TableCell sx={{ fontWeight: 700, width: 140 }} align="center">
                  Korekta WR (%)
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {types.map((t) => {
                const val = getValue(t.id);
                const displayPct = (val * 100).toFixed(2);
                const isEdited = edited.has(t.id);
                return (
                  <TableRow
                    key={t.id}
                    sx={{ "&:hover": { bgcolor: alpha(accent, 0.04) } }}
                  >
                    <TableCell>
                      <Chip
                        label={t.id}
                        size="small"
                        sx={{
                          fontFamily: "monospace",
                          fontWeight: 700,
                          fontSize: "0.7rem",
                          height: 22,
                          bgcolor: alpha(accent, 0.1),
                          color: accent,
                        }}
                      />
                    </TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>{t.name}</TableCell>
                    <TableCell align="center" sx={{ p: 0.5 }}>
                      <TextField
                        size="small"
                        variant="outlined"
                        value={displayPct}
                        onChange={(e) => handleChange(t.id, e.target.value)}
                        sx={{
                          width: 100,
                          "& input": {
                            textAlign: "center",
                            fontSize: "0.85rem",
                            fontWeight: val !== 0 ? "bold" : "normal",
                            color:
                              val > 0 ? "#2e7d32" : val < 0 ? "#c62828" : "inherit",
                            py: 0.5,
                            px: 0.5,
                          },
                          ...(isEdited && {
                            "& .MuiOutlinedInput-root": {
                              borderColor: "#ff9800",
                              bgcolor: alpha("#ff9800", 0.05),
                            },
                          }),
                        }}
                        inputProps={{ step: 0.5 }}
                      />
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}

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

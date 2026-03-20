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

import { apiClient } from '../lib/apiClient';

interface VintageCorrection {
  id: number;
  rocznik: string;
  korekta_procent: number;
}

export default function VintageCorrectionCrudPanel() {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";
  const accent = "#5c6bc0"; // indigo for calendar/vintage

  const [items, setItems] = useState<VintageCorrection[]>([]);
  const [edited, setEdited] = useState<Map<number, number>>(new Map());
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error";
  }>({ open: false, message: "", severity: "success" });

  const fetchItems = async () => {
    setLoading(true);
    try {
      const resp = await apiClient.fetch(`/api/vintage-corrections`);
      if (resp.ok) {
        const data = await resp.json();
        setItems(Array.isArray(data) ? data : []);
        setEdited(new Map());
      }
    } catch (e) {
      console.error("Failed to load vintage corrections", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const getValue = (id: number): number => {
    return edited.has(id)
      ? edited.get(id)!
      : items.find((i) => i.id === id)?.korekta_procent ?? 0;
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
      const payload = Array.from(edited.entries()).map(([id, korekta_procent]) => ({
        id,
        korekta_procent,
      }));
      const resp = await apiClient.fetch(`/api/vintage-corrections/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error("Save failed");
      setSnackbar({
        open: true,
        message: "Zapisano korekty rocznika",
        severity: "success",
      });
      await fetchItems();
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
          📅 Korekta WR za rocznik pojazdu
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
        Korekta WR za rocznik: „bieżący" = aktualny rok produkcji (0%), „bieżący-1" = rok
        wcześniejszy (np. −8% = obniżenie WR).
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
            maxWidth: 500,
          }}
        >
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: alpha(accent, isDark ? 0.1 : 0.04) }}>
                <TableCell sx={{ fontWeight: 700, width: 50 }}>ID</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Rocznik</TableCell>
                <TableCell sx={{ fontWeight: 700, width: 140 }} align="center">
                  Korekta WR (%)
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((item) => {
                const val = getValue(item.id);
                const displayPct = (val * 100).toFixed(2);
                const isEdited = edited.has(item.id);
                return (
                  <TableRow
                    key={item.id}
                    sx={{ "&:hover": { bgcolor: alpha(accent, 0.04) } }}
                  >
                    <TableCell>
                      <Chip
                        label={item.id}
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
                    <TableCell sx={{ fontWeight: 600 }}>{item.rocznik}</TableCell>
                    <TableCell align="center" sx={{ p: 0.5 }}>
                      <TextField
                        size="small"
                        variant="outlined"
                        value={displayPct}
                        onChange={(e) => handleChange(item.id, e.target.value)}
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

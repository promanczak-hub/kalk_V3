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
  TextField,
  MenuItem,
  CircularProgress,
  Snackbar,
  Alert,
  Tooltip,
} from "@mui/material";
import { Save } from "lucide-react";

const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

interface SamarClass {
  id: number;
  name: string;
}

interface EngineType {
  id: number;
  name: string;
  category: string;
}

interface MileageCorrection {
  id?: number;
  samar_class_id: number;
  fuel_type_id: number;
  under_threshold_percent: number;
  over_threshold_percent: number;
}

const getValueColor = (value: number): string => {
  if (value > 0) return "#c62828";
  if (value < 0) return "#2e7d32";
  return "inherit";
};

const formatPercent = (value: number): string => {
  return (value * 100).toFixed(3);
};

const parsePercent = (str: string): number => {
  const val = parseFloat(str);
  if (isNaN(val)) return 0;
  return val / 100;
};

export default function MileageCorrectionsPanel({ samarClassId }: { samarClassId?: number }) {
  const [classes, setClasses] = useState<SamarClass[]>([]);
  const [engines, setEngines] = useState<EngineType[]>([]);
  const [selectedClassId, setSelectedClassId] = useState<number | null>(samarClassId ?? null);
  const [corrections, setCorrections] = useState<MileageCorrection[]>([]);
  const [editedCorrections, setEditedCorrections] = useState<Map<string, MileageCorrection>>(new Map());
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: "success" | "error" }>({
    open: false,
    message: "",
    severity: "success",
  });

  useEffect(() => {
    const fetchMeta = async () => {
      try {
        const [classResp, engineResp] = await Promise.all([
          fetch(`${BASE_URL}/api/samar-classes`),
          fetch(`${BASE_URL}/api/engines`),
        ]);
        const classData: SamarClass[] = classResp.ok ? await classResp.json() : [];
        const engineData: EngineType[] = engineResp.ok ? await engineResp.json() : [];
        setClasses(Array.isArray(classData) ? classData : []);
        setEngines(
          Array.isArray(engineData)
            ? engineData.sort((a, b) => a.id - b.id)
            : []
        );
        if (classData.length > 0) {
          setSelectedClassId(classData[0].id);
        }
      } catch (e) {
        console.error("Failed to load metadata", e);
      }
    };
    fetchMeta();
  }, []);

  // Sync with parent's samarClassId prop
  useEffect(() => {
    if (samarClassId !== undefined) {
      setSelectedClassId(samarClassId);
    }
  }, [samarClassId]);

  const fetchCorrections = useCallback(async () => {
    if (selectedClassId === null) return;
    setLoading(true);
    try {
      const resp = await fetch(`${BASE_URL}/api/mileage-corrections?samar_class_id=${selectedClassId}`);
      const data: MileageCorrection[] = resp.ok ? await resp.json() : [];
      setCorrections(Array.isArray(data) ? data : []);
      setEditedCorrections(new Map());
    } catch (e) {
      console.error("Failed to load corrections", e);
    } finally {
      setLoading(false);
    }
  }, [selectedClassId]);

  useEffect(() => {
    fetchCorrections();
  }, [fetchCorrections]);

  const getCorrection = (engineId: number): MileageCorrection | undefined => {
    return corrections.find((c) => c.fuel_type_id === engineId);
  };

  const getValue = (engineId: number, field: "under" | "over"): number => {
    const key = `${engineId}-${field}`;
    const edited = editedCorrections.get(key);
    if (edited) {
      return field === "under" ? edited.under_threshold_percent : edited.over_threshold_percent;
    }
    const existing = getCorrection(engineId);
    if (existing) {
      return field === "under" ? existing.under_threshold_percent : existing.over_threshold_percent;
    }
    return 0;
  };

  const handleChange = (engineId: number, field: "under" | "over", rawValue: string) => {
    const parsedValue = parsePercent(rawValue);
    const key = `${engineId}-${field}`;

    const existing = getCorrection(engineId);
    const currentUnder = existing?.under_threshold_percent ?? 0;
    const currentOver = existing?.over_threshold_percent ?? 0;

    const updated: MileageCorrection = {
      ...(existing || { samar_class_id: selectedClassId!, fuel_type_id: engineId }),
      under_threshold_percent: field === "under" ? parsedValue : currentUnder,
      over_threshold_percent: field === "over" ? parsedValue : currentOver,
    };

    setEditedCorrections((prev) => {
      const next = new Map(prev);
      next.set(key, updated);
      return next;
    });
  };

  const handleSave = async () => {
    if (editedCorrections.size === 0) return;
    setSaving(true);
    try {
      const uniqueMap = new Map<number, MileageCorrection>();
      for (const correction of editedCorrections.values()) {
        const prev = uniqueMap.get(correction.fuel_type_id);
        uniqueMap.set(correction.fuel_type_id, { ...(prev || {}), ...correction });
      }
      const payload = Array.from(uniqueMap.values());
      await fetch(`${BASE_URL}/api/mileage-corrections/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setSnackbar({ open: true, message: "Zapisano korekty przebiegowe", severity: "success" });
      await fetchCorrections();
    } catch (e) {
      console.error("Failed to save", e);
      setSnackbar({ open: true, message: "Błąd zapisu", severity: "error" });
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = editedCorrections.size > 0;

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h6">Korekty Przebiegowe (per napęd)</Typography>
        <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
          {!samarClassId && (
            <TextField
              select
              size="small"
              label="Klasa SAMAR"
              value={selectedClassId ?? ""}
              onChange={(e) => setSelectedClassId(Number(e.target.value))}
              sx={{ minWidth: 200 }}
            >
              {classes.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.name}
                </MenuItem>
              ))}
            </TextField>
          )}
          <Button
            variant="contained"
            color="primary"
            startIcon={saving ? <CircularProgress size={16} /> : <Save size={16} />}
            onClick={handleSave}
            disabled={!hasChanges || saving}
          >
            Zapisz zmiany
          </Button>
        </Box>
      </Box>

      <Typography variant="caption" color="textSecondary" sx={{ mb: 2, display: "block" }}>
        Wartości w % per 1000 km. „Pod progiem" = korekta za przebieg poniżej normatywnego.
        „Nad progiem" = korekta za nadprzebieg.
      </Typography>

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: "bold" }}>Korekta</TableCell>
                {engines.map((eng) => (
                  <TableCell key={eng.id} align="center" sx={{ fontWeight: "bold", fontSize: "0.75rem", minWidth: 90 }}>
                    <Tooltip title={eng.category}>
                      <span>{eng.name.replace(/\(.*\)/, "").trim()}</span>
                    </Tooltip>
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow hover>
                <TableCell sx={{ fontWeight: "bold" }}>Pod progiem</TableCell>
                {engines.map((eng) => {
                  const val = getValue(eng.id, "under");
                  return (
                    <TableCell key={eng.id} align="center" sx={{ p: 0.5 }}>
                      <TextField
                        size="small"
                        variant="outlined"
                        value={formatPercent(val)}
                        onChange={(e) => handleChange(eng.id, "under", e.target.value)}
                        sx={{
                          width: 85,
                          "& input": {
                            textAlign: "center",
                            fontSize: "0.8rem",
                            color: getValueColor(val),
                            fontWeight: val !== 0 ? "bold" : "normal",
                            py: 0.5,
                            px: 0.5,
                          },
                        }}
                      />
                    </TableCell>
                  );
                })}
              </TableRow>
              <TableRow hover>
                <TableCell sx={{ fontWeight: "bold" }}>Nad progiem</TableCell>
                {engines.map((eng) => {
                  const val = getValue(eng.id, "over");
                  return (
                    <TableCell key={eng.id} align="center" sx={{ p: 0.5 }}>
                      <TextField
                        size="small"
                        variant="outlined"
                        value={formatPercent(val)}
                        onChange={(e) => handleChange(eng.id, "over", e.target.value)}
                        sx={{
                          width: 85,
                          "& input": {
                            textAlign: "center",
                            fontSize: "0.8rem",
                            color: getValueColor(val),
                            fontWeight: val !== 0 ? "bold" : "normal",
                            py: 0.5,
                            px: 0.5,
                          },
                        }}
                      />
                    </TableCell>
                  );
                })}
              </TableRow>
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

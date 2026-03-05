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

interface DepreciationRate {
  id?: number;
  samar_class_id: number;
  fuel_type_id: number;
  year: number;
  base_depreciation_percent: number;
  options_depreciation_percent: number;
}

const MAX_YEARS = 7;

const getValueColor = (value: number): string => {
  if (value > 0) return "#c62828"; // depreciation (red)
  if (value < 0) return "#2e7d32"; // appreciation (green)
  return "inherit";
};

const formatPercent = (value: number): string => {
  return (value * 100).toFixed(2);
};

const parsePercent = (str: string): number => {
  const val = parseFloat(str);
  if (isNaN(val)) return 0;
  return val / 100;
};

export default function DepreciationRatesPanel({ samarClassId }: { samarClassId?: number }) {
  const [classes, setClasses] = useState<SamarClass[]>([]);
  const [engines, setEngines] = useState<EngineType[]>([]);
  const [selectedClassId, setSelectedClassId] = useState<number | null>(samarClassId ?? null);
  const [rates, setRates] = useState<DepreciationRate[]>([]);
  const [editedRates, setEditedRates] = useState<Map<string, DepreciationRate>>(new Map());
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

  const fetchRates = useCallback(async () => {
    if (selectedClassId === null) return;
    setLoading(true);
    try {
      const resp = await fetch(`${BASE_URL}/api/depreciation-rates?samar_class_id=${selectedClassId}`);
      const data: DepreciationRate[] = resp.ok ? await resp.json() : [];
      setRates(Array.isArray(data) ? data : []);
      setEditedRates(new Map());
    } catch (e) {
      console.error("Failed to load rates", e);
    } finally {
      setLoading(false);
    }
  }, [selectedClassId]);

  useEffect(() => {
    fetchRates();
  }, [fetchRates]);

  const getRateKey = (engineId: number, year: number, field: "base" | "options") =>
    `${engineId}-${year}-${field}`;

  const getRate = (engineId: number, year: number): DepreciationRate | undefined => {
    return rates.find((r) => r.fuel_type_id === engineId && r.year === year);
  };

  const getValue = (engineId: number, year: number, field: "base" | "options"): number => {
    const key = getRateKey(engineId, year, field);
    const edited = editedRates.get(key);
    if (edited) {
      return field === "base" ? edited.base_depreciation_percent : edited.options_depreciation_percent;
    }
    const existing = getRate(engineId, year);
    if (existing) {
      return field === "base" ? existing.base_depreciation_percent : existing.options_depreciation_percent;
    }
    return 0;
  };

  const handleChange = (engineId: number, year: number, field: "base" | "options", rawValue: string) => {
    const parsedValue = parsePercent(rawValue);
    const key = getRateKey(engineId, year, field);

    const existing = getRate(engineId, year);
    const currentBase = existing?.base_depreciation_percent ?? 0;
    const currentOptions = existing?.options_depreciation_percent ?? 0;

    const updated: DepreciationRate = {
      ...(existing || { samar_class_id: selectedClassId!, fuel_type_id: engineId, year }),
      base_depreciation_percent: field === "base" ? parsedValue : currentBase,
      options_depreciation_percent: field === "options" ? parsedValue : currentOptions,
    };

    setEditedRates((prev) => {
      const next = new Map(prev);
      next.set(key, updated);
      return next;
    });
  };

  const handleSave = async () => {
    if (editedRates.size === 0) return;
    setSaving(true);
    try {
      // Deduplicate by (engineId, year) — collect unique rates
      const uniqueMap = new Map<string, DepreciationRate>();
      for (const rate of editedRates.values()) {
        const dedupKey = `${rate.fuel_type_id}-${rate.year}`;
        const prev = uniqueMap.get(dedupKey);
        uniqueMap.set(dedupKey, { ...(prev || {}), ...rate });
      }
      const payload = Array.from(uniqueMap.values());
      await fetch(`${BASE_URL}/api/depreciation-rates/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setSnackbar({ open: true, message: "Zapisano zmiany deprecjacji", severity: "success" });
      await fetchRates();
    } catch (e) {
      console.error("Failed to save", e);
      setSnackbar({ open: true, message: "Błąd zapisu", severity: "error" });
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = editedRates.size > 0;

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="h6">Krzywe Deprecjacji/Aprecjacji</Typography>
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
        Wartości w % (np. 8.00 = 8%). Dodatnie = deprecjacja (czerwony). Ujemne = aprecjacja (zielony).
        Edytuj komórkę i kliknij „Zapisz zmiany".
      </Typography>

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
            Deprecjacja bazy (% rocznie)
          </Typography>
          <TableContainer component={Paper} sx={{ mb: 3, maxHeight: 400 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: "bold", position: "sticky", left: 0, zIndex: 3, bgcolor: "background.paper" }}>
                    Rok
                  </TableCell>
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
                {Array.from({ length: MAX_YEARS }, (_, i) => i + 1).map((year) => (
                  <TableRow key={year} hover>
                    <TableCell sx={{ fontWeight: "bold", position: "sticky", left: 0, bgcolor: "background.paper" }}>
                      Rok {year}
                    </TableCell>
                    {engines.map((eng) => {
                      const val = getValue(eng.id, year, "base");
                      return (
                        <TableCell key={eng.id} align="center" sx={{ p: 0.5 }}>
                          <TextField
                            size="small"
                            variant="outlined"
                            value={formatPercent(val)}
                            onChange={(e) => handleChange(eng.id, year, "base", e.target.value)}
                            sx={{
                              width: 75,
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
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
            Deprecjacja opcji (% rocznie)
          </Typography>
          <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: "bold", position: "sticky", left: 0, zIndex: 3, bgcolor: "background.paper" }}>
                    Rok
                  </TableCell>
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
                {Array.from({ length: MAX_YEARS }, (_, i) => i + 1).map((year) => (
                  <TableRow key={year} hover>
                    <TableCell sx={{ fontWeight: "bold", position: "sticky", left: 0, bgcolor: "background.paper" }}>
                      Rok {year}
                    </TableCell>
                    {engines.map((eng) => {
                      const val = getValue(eng.id, year, "options");
                      return (
                        <TableCell key={eng.id} align="center" sx={{ p: 0.5 }}>
                          <TextField
                            size="small"
                            variant="outlined"
                            value={formatPercent(val)}
                            onChange={(e) => handleChange(eng.id, year, "options", e.target.value)}
                            sx={{
                              width: 75,
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
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
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

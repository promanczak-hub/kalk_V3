import { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  TextField,
  InputAdornment,
  CircularProgress,
} from "@mui/material";
import { Save as SaveIcon } from "@mui/icons-material";

const BASE_URL = "http://127.0.0.1:8000";

interface BaseRVRate {
  id?: number;
  samar_class_id: number;
  engine_type_id: number;
  base_rv_percent: number;
  engines?: { name: string };
}

export default function BaseRVCrudPanel({
  samarClassId,
}: {
  samarClassId: number;
}) {
  const [rates, setRates] = useState<BaseRVRate[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    fetchRates();
  }, [samarClassId]);

  const fetchRates = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${BASE_URL}/api/samar-class-base-rv/${samarClassId}`);
      const data = await resp.json();
      setRates(data || []);
      setHasChanges(false);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handlePercentChange = (engineTypeId: number, valStr: string) => {
    let val = parseFloat(valStr);
    if (isNaN(val)) val = 0;
    
    setRates((prev) =>
      prev.map((r) =>
        r.engine_type_id === engineTypeId
          ? { ...r, base_rv_percent: val / 100 }
          : r
      )
    );
    setHasChanges(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // payload expects array of {engine_type_id, base_rv_percent}
      const payload = rates.map((r) => ({
        engine_type_id: r.engine_type_id,
        base_rv_percent: r.base_rv_percent,
      }));
      await fetch(`${BASE_URL}/api/samar-class-base-rv/${samarClassId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setHasChanges(false);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <CircularProgress sx={{ display: "block", m: "2rem auto" }} />;

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2, alignItems: "center" }}>
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Bazowa Utrata Wartości (Monolit 1)
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            Stałe wartości bazowego WR w zależności od napędu. Te wartości służą jako punkt wyjścia. Zmiany aplikują się natychmiast dla wszystkich aut z danej klasy SAMAR.
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          disabled={!hasChanges || saving}
          onClick={handleSave}
          color={hasChanges ? "warning" : "primary"}
        >
          {saving ? "Zapisywanie..." : "Zapisz Zmiany"}
        </Button>
      </Box>

      {rates.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          Brak danych bazowego WR dla tej klasy.
        </Typography>
      ) : (
        <TableContainer component={Paper} elevation={0} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: "background.default" }}>
                <TableCell sx={{ fontWeight: 600 }}>ID Napędu</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Rodzaj Napędu (Silnik)</TableCell>
                <TableCell sx={{ fontWeight: 600, width: 250 }}>Wartość % (0-100)</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rates.map((row) => (
                <TableRow key={row.engine_type_id} hover>
                  <TableCell sx={{ color: "text.secondary", fontFamily: "monospace" }}>{row.engine_type_id}</TableCell>
                  <TableCell sx={{ fontWeight: 500 }}>{row.engines?.name || "Nieznany"}</TableCell>
                  <TableCell>
                    <TextField
                      size="small"
                      type="number"
                      value={(row.base_rv_percent * 100).toFixed(1)}
                      onChange={(e) => handlePercentChange(row.engine_type_id, e.target.value)}
                      InputProps={{
                        endAdornment: <InputAdornment position="end">%</InputAdornment>,
                      }}
                      sx={{ width: 120, bgcolor: "background.paper", "& .MuiInputBase-input": { textAlign: "right", fontWeight: 600 } }}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}

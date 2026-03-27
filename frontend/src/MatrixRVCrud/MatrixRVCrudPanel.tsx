import { useState, useEffect } from "react";
import {
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Typography,
} from "@mui/material";
import { supabase } from "../lib/supabaseClient";
import { apiClient } from "../lib/apiClient";
import { API_BASE_URL } from "../config/env";
import ConfigTableToolbar from "../components/ConfigTableToolbar";

interface SamarClass {
  id: number;
  name: string;
}

interface Engine {
  id: number;
  name: string;
}

export default function MatrixRVCrudPanel() {
  const [classes, setClasses] = useState<SamarClass[]>([]);
  const [engines, setEngines] = useState<Engine[]>([]);
  const [matrix, setMatrix] = useState<Record<number, Record<number, number>>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  const [changedRows, setChangedRows] = useState<Set<number>>(new Set());

  const fetchData = async () => {
    setLoading(true);
    try {
      const { data: classData, error: classErr } = await supabase
        .from("samar_classes")
        .select("id, name")
        .order("id", { ascending: true });
      if (classErr) throw classErr;
      setClasses(classData || []);

      const { data: engineData, error: engineErr } = await supabase
        .from("engines")
        .select("id, name")
        .order("id", { ascending: true });
      if (engineErr) throw engineErr;
      setEngines(engineData || []);

      const res = await apiClient.fetch(`${API_BASE_URL}/api/samar-class-base-rv`);
      if (res.ok) {
        const matrixData = await res.json();
        const newMatrix: Record<number, Record<number, number>> = {};
        for (const item of matrixData) {
          if (!newMatrix[item.samar_class_id]) newMatrix[item.samar_class_id] = {};
          newMatrix[item.samar_class_id][item.engine_type_id] = item.base_rv_percent;
        }
        setMatrix(newMatrix);
        setHasChanges(false);
        setChangedRows(new Set());
      }
    } catch (err) {
      console.error("Error fetching Base RV data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCellChange = (classId: number, engineId: number, valueStr: string) => {
    let val = parseFloat(valueStr.replace(',', '.'));
    if (isNaN(val)) val = 0;

    setMatrix((prev) => ({
      ...prev,
      [classId]: {
        ...(prev[classId] || {}),
        [engineId]: val,
      },
    }));
    setHasChanges(true);
    setChangedRows((prev) => new Set(prev).add(classId));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = Array.from(changedRows).flatMap((classId) => {
        const rowData = matrix[classId] || {};
        return Object.entries(rowData).map(([engId, value]) => ({
          samar_class_id: classId,
          engine_type_id: parseInt(engId, 10),
          base_rv_percent: value,
        }));
      });

      if (payload.length === 0) {
        setHasChanges(false);
        setSaving(false);
        return;
      }

      const res = await apiClient.fetch(`${API_BASE_URL}/api/samar-class-base-rv/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Bulk save failed");

      setHasChanges(false);
      setChangedRows(new Set());
      await fetchData();
    } catch (err) {
      console.error("Error saving Base RV matrix:", err);
      alert("Wystąpił błąd podczas zapisu.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 4, display: "flex", justifyContent: "center" }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2, alignItems: 'center' }}>
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>Tabela wartości rezydualnych (Base RV)</Typography>
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            Pełna matryca wartości bazowych. (Edytowalna jako procent: np. wpisz 0.32 dla 32%)
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <ConfigTableToolbar tableName="samar_class_base_rv" tableLabel="Base RV" onDataChanged={fetchData} />
          <Button
            variant="contained"
            color={hasChanges ? "warning" : "primary"}
            onClick={handleSave}
            disabled={!hasChanges || saving}
          >
            {saving ? "Zapisuję..." : "Zapisz Zmiany"}
          </Button>
        </Box>
      </Box>

      <TableContainer component={Paper} sx={{ maxHeight: "70vh", overflow: "auto", border: "1px solid #e0e0e0" }}>
        <Table stickyHeader size="small" sx={{ minWidth: 1000, "& th, & td": { borderRight: "1px solid #f0f0f0" } }}>
          <TableHead>
            <TableRow>
              <TableCell sx={{ minWidth: 250, fontWeight: "bold", bgcolor: "#fafafa", zIndex: 10, position: 'sticky', left: 0 }}>Klasa SAMAR</TableCell>
              {engines.map((e) => (
                <TableCell key={e.id} align="center" sx={{ fontWeight: "bold", bgcolor: "#fafafa", minWidth: 100 }}>
                  {e.name}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {classes.map((c) => (
              <TableRow key={c.id} hover>
                <TableCell sx={{ fontWeight: 500, fontSize: "0.85rem", bgcolor: "#fff", position: 'sticky', left: 0, zIndex: 5, borderRight: "1px solid #e0e0e0" }}>{c.name}</TableCell>
                {engines.map((e) => {
                  const val = matrix[c.id]?.[e.id] ?? "";
                  return (
                    <TableCell key={e.id} align="center" sx={{ p: 0.5 }}>
                      <input
                        type="number"
                        step="0.01"
                        value={val}
                        style={{
                          width: "90%",
                          padding: "6px",
                          border: "1px solid transparent",
                          borderRadius: "4px",
                          textAlign: "center",
                          outline: "none",
                        }}
                        onFocus={(el) => (el.target.style.border = "1px solid #1976d2")}
                        onBlur={(el) => (el.target.style.border = "1px solid transparent")}
                        onChange={(ev) => handleCellChange(c.id, e.id, ev.target.value)}
                      />
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

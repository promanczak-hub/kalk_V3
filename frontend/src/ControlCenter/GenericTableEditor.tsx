import { useState, useEffect, useCallback, useMemo } from "react";
import {
  Box,
  Snackbar,
  Alert,
  CircularProgress,
  Button,
  Typography,
  Divider,
  IconButton,
  alpha,
} from "@mui/material";
import {
  DataGrid,
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarFilterButton,
  GridToolbarDensitySelector,
  GridActionsCellItem,
} from "@mui/x-data-grid";
import type { GridColDef, GridRowId } from "@mui/x-data-grid";
import AddIcon from "@mui/icons-material/Add";
import SaveIcon from "@mui/icons-material/Save";
import DeleteIcon from "@mui/icons-material/Delete";
import RefreshIcon from "@mui/icons-material/Refresh";
import { v4 as uuidv4 } from "uuid";

import { apiClient } from "../lib/apiClient";

interface GenericTableEditorProps {
  tableName: string;
}

export default function GenericTableEditor({ tableName }: GenericTableEditorProps) {
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error";
  }>({
    open: false,
    message: "",
    severity: "success",
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.fetch(`/api/config/${tableName}/rows`);
      if (!res.ok) throw new Error("Nie udało się pobrać danych");
      const data = await res.json();
      
      // Ensure all rows have an ID (if DB id is missing, use UUID)
      const mappedRows = data.map((r: Record<string, unknown>) => ({
        ...r,
        id: r.id !== undefined ? r.id : `new-${uuidv4()}`,
      }));
      setRows(mappedRows);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Błąd pobierania danych";
      setSnackbar({ open: true, message, severity: "error" });
    } finally {
      setLoading(false);
    }
  }, [tableName]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Dynamically generate columns from the first row or common patterns
  const columns = useMemo(() => {
    if (rows.length === 0) return [];
    
    // Get all keys from all rows (in case mapping is sparse)
    const allKeys = Array.from(new Set(rows.flatMap(r => Object.keys(r))));
    
    const cols: GridColDef[] = allKeys.map((key) => {
      const isId = key.toLowerCase() === "id";
      const isDate = key.toLowerCase().includes("at");
      
      return {
        field: key,
        headerName: key.toUpperCase(),
        flex: 1,
        minWidth: 120,
        editable: !isId && !isDate, // Don't edit internal fields
        type: typeof (rows[0] as any)[key] === "number" ? "number" : "string",
      };
    });

    // Add Delete Action
    cols.push({
      field: "actions",
      type: "actions",
      headerName: "Opcje",
      width: 80,
      getActions: (params) => [
        <GridActionsCellItem
          icon={<DeleteIcon />}
          label="Usuń"
          onClick={() => handleDeleteRow(params.id)}
          color="inherit"
        />,
      ],
    });

    return cols;
  }, [rows]);

  const handleDeleteRow = (id: GridRowId) => {
    setRows((prev) => prev.filter((r) => r.id !== id));
  };

  const handleAddRow = () => {
    const newRow = { id: `new-${uuidv4()}` } as Record<string, unknown>;
    setRows((prev) => [newRow, ...prev]);
  };

  const handleProcessRowUpdate = (newRow: Record<string, unknown>, oldRow: Record<string, unknown>) => {
    if (JSON.stringify(newRow) === JSON.stringify(oldRow)) return newRow;
    const updatedRows = rows.map((r) => (r.id === newRow.id ? newRow : r));
    setRows(updatedRows);
    return newRow;
  };

  const handleSaveBulk = async () => {
    setSaving(true);
    try {
      // Backend expects 'id' for updates, but our 'new-UUID' should be stripped or handled as insert
      const cleanedRows = rows.map(r => {
        const rowData = { ...r };
        if (typeof rowData.id === "string" && rowData.id.startsWith("new-")) {
          delete rowData.id;
        }
        return rowData;
      });

      const res = await apiClient.fetch(`/api/config/${tableName}/rows`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cleanedRows),
      });

      if (!res.ok) throw new Error("Błąd podczas zapisywania bulk");
      
      setSnackbar({ open: true, message: "Pomyślnie zsynchronizowano z bazą", severity: "success" });
      fetchData(); // Refresh to get real IDs
    } catch (err) {
      const message = err instanceof Error ? err.message : "Błąd zapisu bulk";
      setSnackbar({ open: true, message, severity: "error" });
    } finally {
      setSaving(false);
    }
  };

  function CustomToolbar() {
    return (
      <GridToolbarContainer sx={{ p: 1, gap: 1 }}>
        <Button size="small" variant="outlined" startIcon={<AddIcon />} onClick={handleAddRow}>
          Dodaj Wiersz
        </Button>
        <Button 
          size="small" 
          variant="contained" 
          color="primary" 
          startIcon={<SaveIcon />} 
          onClick={handleSaveBulk}
          disabled={saving}
        >
          {saving ? "Zapisywanie..." : "Zapisz Zmiany (Bulk)"}
        </Button>
        <Divider orientation="vertical" flexItem />
        <GridToolbarColumnsButton />
        <GridToolbarFilterButton />
        <GridToolbarDensitySelector />
        <Box sx={{ flexGrow: 1 }} />
        <IconButton size="small" onClick={fetchData}>
          <RefreshIcon />
        </IconButton>
      </GridToolbarContainer>
    );
  }

  if (loading && rows.length === 0) {
    return (
      <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", justifyItems: "center", gap: 2, p: 10 }}>
        <CircularProgress size={60} />
        <Typography variant="overline" color="text.secondary">Pobieranie danych tabeli [{tableName}]...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flexGrow: 1, minHeight: 400 }}>
        <DataGrid
          rows={rows}
          columns={columns}
          slots={{ toolbar: CustomToolbar }}
          processRowUpdate={handleProcessRowUpdate}
          onProcessRowUpdateError={(err) => setSnackbar({ open: true, message: err.message, severity: "error" })}
          density="compact"
          disableRowSelectionOnClick
          sx={{
            border: 'none',
            '& .MuiDataGrid-cell--editable': {
              bgcolor: (theme) => alpha(theme.palette.primary.main, 0.04),
              cursor: 'cell'
            }
          }}
        />
      </Box>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

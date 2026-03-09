import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Box,
  Button,
  Toolbar,
  Typography,
  Snackbar,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  CircularProgress
} from "@mui/material";
import {
  DataGrid,
  GridToolbarContainer,
  useGridApiRef
} from "@mui/x-data-grid";
import type { GridColDef, GridRowModel } from "@mui/x-data-grid";
import AddIcon from "@mui/icons-material/Add";
import SaveIcon from "@mui/icons-material/Save";
import { v4 as uuidv4 } from "uuid";

interface ColumnDef {
  field: string;
  headerName: string;
  width?: number;
}

interface ExcelDraftSheet {
  id?: number;
  sheet_name: string;
  columns_def: ColumnDef[];
  data_rows: any[];
}

interface DynamicGridEditorProps {
  sheetName: string;
}

export default function DynamicGridEditor({ sheetName }: DynamicGridEditorProps) {
  const [rows, setRows] = useState<any[]>([]);
  const [columns, setColumns] = useState<GridColDef[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: "success" | "error" }>({
    open: false,
    message: "",
    severity: "success",
  });
  
  const [newColDialog, setNewColDialog] = useState(false);
  const [newColName, setNewColName] = useState("");
  
  const apiRef = useGridApiRef();

  const fetchSheet = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/excel-drafts/${encodeURIComponent(sheetName)}`);
      if (!res.ok) {
        throw new Error("Failed to fetch sheet");
      }
      const data: ExcelDraftSheet = await res.json();
      
      const mappedCols: GridColDef[] = data.columns_def.map((c) => ({
        field: c.field,
        headerName: c.headerName,
        width: c.width || 150,
        editable: true,
      }));
      
      setColumns(mappedCols);
      
      const mappedRows = data.data_rows.map((r, idx) => ({
        ...r,
        id: r.id || uuidv4()
      }));
      setRows(mappedRows);
    } catch (err: any) {
      setSnackbar({ open: true, message: err.message, severity: "error" });
    } finally {
      setLoading(false);
    }
  }, [sheetName]);

  useEffect(() => {
    if (sheetName) {
      fetchSheet();
    }
  }, [sheetName, fetchSheet]);

  const processRowUpdate = (newRow: GridRowModel, oldRow: GridRowModel) => {
    const updatedRows = rows.map((r) => (r.id === newRow.id ? newRow : r));
    setRows(updatedRows);
    return newRow;
  };

  const handleAddRow = () => {
    const newRow: any = { id: uuidv4() };
    columns.forEach((c) => {
      newRow[c.field] = "";
    });
    setRows([...rows, newRow]);
  };

  const handleAddColumn = () => {
    if (!newColName.trim()) return;
    
    // Create safe field name (lowercase, no spaces)
    const fieldName = "col_" + newColName.toLowerCase().replace(/[^a-z0-9]/g, "_") + "_" + Date.now();
    
    const newCol: GridColDef = {
      field: fieldName,
      headerName: newColName,
      width: 150,
      editable: true,
    };
    
    setColumns([...columns, newCol]);
    
    // Add empty field to existing rows
    const updatedRows = rows.map((r) => ({ ...r, [fieldName]: "" }));
    setRows(updatedRows);
    
    setNewColDialog(false);
    setNewColName("");
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Map back our frontend formats to backend formats
      const colsToSave = columns.map(c => ({
        field: c.field,
        headerName: c.headerName,
        width: c.width as number
      }));
      
      const payload = {
        columns_def: colsToSave,
        data_rows: rows
      };
      
      const res = await fetch(`http://127.0.0.1:8000/api/excel-drafts/${encodeURIComponent(sheetName)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        throw new Error("Failed to save sheet");
      }
      
      setSnackbar({ open: true, message: "Arkusz został zapisany pomyślnie!", severity: "success" });
    } catch (err: any) {
      setSnackbar({ open: true, message: err.message, severity: "error" });
    } finally {
      setSaving(false);
    }
  };

  function CustomToolbar() {
    return (
      <GridToolbarContainer sx={{ p: 1, gap: 1 }}>
        <Button color="primary" startIcon={<AddIcon />} onClick={handleAddRow}>
          Dodaj Wiersz
        </Button>
        <Button color="secondary" startIcon={<AddIcon />} onClick={() => setNewColDialog(true)}>
          Dodaj Kolumnę
        </Button>
        <Box sx={{ flexGrow: 1 }} />
        <Button
          color="success"
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? "Zapisywanie..." : "Zapisz Arkusz"}
        </Button>
      </GridToolbarContainer>
    );
  }

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ height: 600, width: "100%" }}>
      <DataGrid
        apiRef={apiRef}
        rows={rows}
        columns={columns}
        processRowUpdate={processRowUpdate}
        slots={{ toolbar: CustomToolbar }}
        disableRowSelectionOnClick
      />

      <Dialog open={newColDialog} onClose={() => setNewColDialog(false)}>
        <DialogTitle>Dodaj nową kolumnę</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Nazwa kolumny (Header)"
            type="text"
            fullWidth
            variant="outlined"
            value={newColName}
            onChange={(e) => setNewColName(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setNewColDialog(false)}>Anuluj</Button>
          <Button onClick={handleAddColumn} variant="contained" disabled={!newColName.trim()}>
            Dodaj
          </Button>
        </DialogActions>
      </Dialog>

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

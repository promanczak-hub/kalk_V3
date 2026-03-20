import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Snackbar,
  Alert,
  CircularProgress,
  Chip
} from "@mui/material";
import {
  DataGrid,
  useGridApiRef
} from "@mui/x-data-grid";
import type { GridColDef } from "@mui/x-data-grid";
import LockIcon from "@mui/icons-material/Lock";
import { v4 as uuidv4 } from "uuid";
import { API_BASE_URL } from "../config/env";
import { apiClient } from "../lib/apiClient";

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
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: "success" | "error" }>({
    open: false,
    message: "",
    severity: "success",
  });
  
  const apiRef = useGridApiRef();

  const fetchSheet = useCallback(async () => {
    setLoading(true);
    try {
      const classesRes = await apiClient.fetch(`${API_BASE_URL}/api/samar-classes`);
      let classNames: string[] = [];
      if (classesRes.ok) {
        const classData = await classesRes.json();
        classNames = classData.map((c: any) => c.name);
      }
      
      const bodyTypesRes = await apiClient.fetch(`${API_BASE_URL}/api/body-types`);
      let bodyTypeNames: string[] = [];
      if (bodyTypesRes.ok) {
        const bodyTypes = await bodyTypesRes.json();
        bodyTypeNames = bodyTypes.map((b: any) => `${b.vehicle_class} - ${b.name}`);
      }

      const res = await apiClient.fetch(`${API_BASE_URL}/api/excel-drafts/${encodeURIComponent(sheetName)}`);
      if (!res.ok) {
        throw new Error("Failed to fetch sheet");
      }
      const data: ExcelDraftSheet = await res.json();
      
      const mappedCols: GridColDef[] = data.columns_def.map((c) => {
        const isClass = c.headerName.toLowerCase().includes("klasa");
        const isBodyType = c.headerName.toLowerCase().includes("nadwozi");
        
        let options: string[] | undefined = undefined;
        if (isClass) {
          const existingValues = data.data_rows.map(r => r[c.field]).filter(Boolean);
          options = Array.from(new Set([...classNames, ...existingValues])) as string[];
        } else if (isBodyType) {
          const existingValues = data.data_rows.map(r => r[c.field]).filter(Boolean);
          options = Array.from(new Set([...bodyTypeNames, ...existingValues])) as string[];
        }
        
        return {
          field: c.field,
          headerName: c.headerName,
          width: c.width || 150,
          editable: false,
          type: (isClass || isBodyType) ? 'singleSelect' : 'string',
          valueOptions: options,
        };
      });
      
      setColumns(mappedCols);
      
      const mappedRows = data.data_rows.map((r) => ({
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

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ height: 600, width: "100%", position: "relative" }}>
      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
        <Chip
          icon={<LockIcon fontSize="small" />}
          label="ZAMROŻONE"
          color="error"
          variant="filled"
          size="small"
        />
      </Box>
      <DataGrid
        apiRef={apiRef}
        rows={rows}
        columns={columns}
        disableRowSelectionOnClick
      />

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


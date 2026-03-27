import { useState } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  Snackbar,
  Alert,
} from "@mui/material";
import {
  DataGrid,
  type GridColDef,
  type GridRowModel,
  type GridRowModesModel,
} from "@mui/x-data-grid";
import { useMileageAdjustments, type MileageAdjustment } from "./useMileageAdjustments";

export default function MileageAdjustmentsCrudPanel() {
  const { data, isLoading, error, updateAdjustment } = useMileageAdjustments();
  const [rowModesModel, setRowModesModel] = useState<GridRowModesModel>({});
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: "success" | "error" }>({
    open: false,
    message: "",
    severity: "success",
  });

  const processRowUpdate = async (newRow: GridRowModel) => {
    const originalRow = data?.find((r: MileageAdjustment) => r.id === newRow.id);
    if (!originalRow) return newRow;

    const payload = {
      max_mileage_target: Number(newRow.max_mileage_target),
      correction_below_threshold: Number(newRow.correction_below_threshold),
      correction_above_threshold: Number(newRow.correction_above_threshold),
    };

    try {
      await updateAdjustment({ id: newRow.id, update: payload });
      setSnackbar({ open: true, message: "Zaktualizowano rekord", severity: "success" });
      return { ...originalRow, ...payload };
    } catch (err) {
      console.error(err);
      setSnackbar({ open: true, message: "Błąd podczas zapisu", severity: "error" });
      throw err;
    }
  };

  const columns: GridColDef[] = [
    { field: "samar_class_id", headerName: "ID Klasy", width: 80 },
    { field: "samar_class_name", headerName: "Klasa SAMAR", width: 250, flex: 1 },
    {
      field: "max_mileage_target",
      headerName: "Max. Przebieg Końcowy",
      type: "number",
      width: 180,
      editable: true,
    },
    {
      field: "correction_below_threshold",
      headerName: "Korekta < Próg (Rabat)",
      type: "number",
      width: 180,
      editable: true,
    },
    {
      field: "correction_above_threshold",
      headerName: "Korekta > Próg (Zwyżka)",
      type: "number",
      width: 180,
      editable: true,
    },
  ];

  if (isLoading) {
    return (
      <Box sx={{ p: 4, display: "flex", justifyContent: "center" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 4, color: "error.main" }}>
        <Typography>Błąd pobierania danych: {(error as Error).message}</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ width: "100%", height: "100%", typography: "body1", p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Korekty wartości rezydualnej w zależności od przebiegu (TAB. PRZEBIEG)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Wartości edytuje się podwójnym kliknięciem lub naciśnięciem Enter, a zapisuje opuszczeniem komórki.
      </Typography>

      <Box sx={{ height: 600, width: "100%", mt: 2 }}>
        <DataGrid
          rows={data || []}
          columns={columns}
          editMode="row"
          rowModesModel={rowModesModel}
          onRowModesModelChange={setRowModesModel}
          processRowUpdate={processRowUpdate}
          onProcessRowUpdateError={(err) => console.error("ProcessRowUpdate error:", err)}
          disableRowSelectionOnClick
          density="compact"
        />
      </Box>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
      >
        <Alert severity={snackbar.severity} sx={{ width: "100%" }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

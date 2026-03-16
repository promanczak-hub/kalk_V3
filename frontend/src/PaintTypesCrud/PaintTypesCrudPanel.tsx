import React, { useState, useEffect } from "react";
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  IconButton,
} from "@mui/material";
import { Edit, Delete } from "@mui/icons-material";
import ConfigTableToolbar from '../components/ConfigTableToolbar';

// Initialize Supabase client
import { supabase } from "../lib/supabaseClient";

interface PaintTypeRecord {
  id?: number;
  name: string;
  wr_correction: number;
}

export default function PaintTypesCrudPanel() {
  const [records, setRecords] = useState<PaintTypeRecord[]>([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingRecord, setEditingRecord] = useState<PaintTypeRecord | null>(null);

  const [formData, setFormData] = useState<PaintTypeRecord>({
    name: "",
    wr_correction: 0,
  });

  const fetchRecords = async () => {
    const { data, error } = await supabase
      .from("paint_types")
      .select("*")
      .order("id", { ascending: true });

    if (error) {
      console.error("Error fetching paint_types:", error);
    } else {
      setRecords(data || []);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, []);

  const handleOpenDialog = (record?: PaintTypeRecord) => {
    if (record) {
      setEditingRecord(record);
      setFormData(record);
    } else {
      setEditingRecord(null);
      setFormData({
        name: "",
        wr_correction: 0,
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    let parsedValue: string | number = value;

    if (name === "wr_correction") {
      parsedValue = parseFloat(value) || 0;
    }

    setFormData((prev) => ({ ...prev, [name]: parsedValue }));
  };

  const handleSave = async () => {
    if (editingRecord?.id) {
      // Update
      const { error } = await supabase
        .from("paint_types")
        .update(formData)
        .eq("id", editingRecord.id);

      if (error) {
        console.error("Error updating record:", error);
      } else {
        fetchRecords();
        handleCloseDialog();
      }
    } else {
      // Create
      const { error } = await supabase.from("paint_types").insert([formData]);

      if (error) {
        console.error("Error creating record:", error);
      } else {
        fetchRecords();
        handleCloseDialog();
      }
    }
  };

  const handleDelete = async (id?: number) => {
    if (!id) return;
    if (window.confirm("Na pewno usunąć ten typ lakieru?")) {
      const { error } = await supabase
        .from("paint_types")
        .delete()
        .eq("id", id);
      if (error) console.error("Error deleting record:", error);
      else fetchRecords();
    }
  };

  return (
    <Box sx={{ p: 4 }}>
      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2, alignItems: 'center' }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <ConfigTableToolbar tableName="paint_types" tableLabel="Kolor (Wycena)" onDataChanged={fetchRecords} />
          <Button
            variant="contained"
            color="primary"
            onClick={() => handleOpenDialog()}
          >
            + Dodaj Kolor
          </Button>
        </Box>
      </Box>

      <TableContainer component={Paper} sx={{ maxHeight: "70vh", overflow: "auto" }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: "bold", width: "120px" }}>Akcje</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Id</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Nazwa (Kolor)</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Korekta WR (%)</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {records.map((r) => (
              <TableRow key={r.id}>
                <TableCell>
                  <IconButton size="small" color="primary" onClick={() => handleOpenDialog(r)}>
                    <Edit fontSize="small" />
                  </IconButton>
                  <IconButton size="small" color="error" onClick={() => handleDelete(r.id)}>
                    <Delete fontSize="small" />
                  </IconButton>
                </TableCell>
                <TableCell>{r.id}</TableCell>
                <TableCell>{r.name}</TableCell>
                <TableCell>{r.wr_correction !== undefined && r.wr_correction !== null ? `${(r.wr_correction * 100).toFixed(2)}%` : "-"}</TableCell>
              </TableRow>
            ))}
            {records.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} sx={{ textAlign: "center", py: 4 }}>
                  Brak zapisanych typów lakieru.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Dialog for Add/Edit */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingRecord ? "Edytuj Kolor" : "Dodaj Nowy Kolor"}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          <TextField
            label="Nazwa (np. Metalizowany, Niemetalizowany)"
            name="name"
            value={formData.name || ""}
            onChange={handleChange}
            fullWidth
            required
          />
          <TextField
            label="Korekta WR (jako ułamek dziesiętny np. -0.01 dla -1%)"
            name="wr_correction"
            type="number"
            inputProps={{ step: "0.01" }}
            value={formData.wr_correction}
            onChange={handleChange}
            fullWidth
          />
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={handleCloseDialog} color="inherit">
            Anuluj
          </Button>
          <Button onClick={handleSave} variant="contained" color="primary">
            Zapisz
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

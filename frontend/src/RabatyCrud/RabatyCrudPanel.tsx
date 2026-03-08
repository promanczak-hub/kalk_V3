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
  MenuItem,
  Select,
  FormControl,
  InputLabel,
} from "@mui/material";
import { Edit, Delete } from "@mui/icons-material";
import { createClient } from "@supabase/supabase-js";
import ConfigTableToolbar from '../components/ConfigTableToolbar';

// Initialize Supabase client
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || "";
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || "";
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

interface RabatyRecord {
  id?: number;
  marka: string;
  model: string;
  kod?: string;
  wykluczenia?: string;
  rabat?: number;
}

const BRANDS = ["SKODA", "AUDI", "VW Osobowe", "VW Dostawcze", "SEAT/CUPRA", "BMW"];

export default function RabatyCrudPanel() {
  const [records, setRecords] = useState<RabatyRecord[]>([]);
  const [filteredRecords, setFilteredRecords] = useState<RabatyRecord[]>([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingRecord, setEditingRecord] = useState<RabatyRecord | null>(null);
  const [filterBrand, setFilterBrand] = useState<string>("All");

  const [formData, setFormData] = useState<RabatyRecord>({
    marka: "SKODA",
    model: "",
    kod: "",
    wykluczenia: "",
    rabat: 0,
  });

  const fetchRecords = async () => {
    const { data, error } = await supabase
      .from("tabela_rabaty")
      .select("*")
      .order("id", { ascending: true });

    if (error) {
      console.error("Error fetching rabaty:", error);
    } else {
      setRecords(data || []);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, []);

  useEffect(() => {
    if (filterBrand === "All") {
      setFilteredRecords(records);
    } else {
      setFilteredRecords(records.filter((r) => r.marka === filterBrand));
    }
  }, [records, filterBrand]);

  const handleOpenDialog = (record?: RabatyRecord) => {
    if (record) {
      setEditingRecord(record);
      setFormData(record);
    } else {
      setEditingRecord(null);
      setFormData({
        marka: filterBrand !== "All" ? filterBrand : "SKODA",
        model: "",
        kod: "",
        wykluczenia: "",
        rabat: 0,
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | { name?: string; value: unknown }>) => {
    const name = e.target.name as keyof RabatyRecord;
    let value: string | number = e.target.value as string;

    if (name === "rabat") {
      value = parseFloat(value as string) || 0;
    }

    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    if (editingRecord?.id) {
      // Update
      const { error } = await supabase
        .from("tabela_rabaty")
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
      const { error } = await supabase.from("tabela_rabaty").insert([formData]);

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
    if (window.confirm("Na pewno usunąć ten rekord?")) {
      const { error } = await supabase
        .from("tabela_rabaty")
        .delete()
        .eq("id", id);
      if (error) console.error("Error deleting record:", error);
      else fetchRecords();
    }
  };

  return (
    <Box sx={{ p: 4 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2, alignItems: 'center' }}>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel id="brand-filter-label">Filtruj Markę</InputLabel>
          <Select
            labelId="brand-filter-label"
            value={filterBrand}
            label="Filtruj Markę"
            onChange={(e) => setFilterBrand(e.target.value)}
          >
            <MenuItem value="All">Wszystkie Marki</MenuItem>
            {BRANDS.map(b => (
              <MenuItem key={b} value={b}>{b}</MenuItem>
            ))}
          </Select>
        </FormControl>

        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <ConfigTableToolbar tableName="tabela_rabaty" tableLabel="Tabela Rabatów" onDataChanged={fetchRecords} />
          <Button
            variant="contained"
            color="primary"
            onClick={() => handleOpenDialog()}
          >
            + Dodaj Rekord
          </Button>
        </Box>
      </Box>

      <TableContainer component={Paper} sx={{ maxHeight: "70vh", overflow: "auto" }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: "bold" }}>Akcje</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Id</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Marka</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Model</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Kod</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Wykluczenia</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Rabat (%)</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredRecords.map((r) => (
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
                <TableCell>{r.marka}</TableCell>
                <TableCell>{r.model}</TableCell>
                <TableCell>{r.kod || "-"}</TableCell>
                <TableCell>{r.wykluczenia || "-"}</TableCell>
                <TableCell>{r.rabat !== undefined && r.rabat !== null ? `${(r.rabat * 100).toFixed(2)}%` : "-"}</TableCell>
              </TableRow>
            ))}
            {filteredRecords.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} sx={{ textAlign: "center", py: 4 }}>
                  Brak danych dla wybranej marki.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Dialog for Add/Edit */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingRecord ? "Edytuj Rekord" : "Dodaj Nowy Rekord"}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          <TextField
            select
            label="Marka"
            name="marka"
            value={formData.marka}
            onChange={handleChange as any}
            fullWidth
            required
          >
            {BRANDS.map(b => (
              <MenuItem key={b} value={b}>{b}</MenuItem>
            ))}
          </TextField>
          <TextField
            label="Model"
            name="model"
            value={formData.model || ""}
            onChange={handleChange}
            fullWidth
            required
          />
          <TextField
            label="Kod"
            name="kod"
            value={formData.kod || ""}
            onChange={handleChange}
            fullWidth
          />
          <TextField
            label="Wykluczenia"
            name="wykluczenia"
            value={formData.wykluczenia || ""}
            onChange={handleChange}
            fullWidth
            multiline
            rows={2}
          />
          <TextField
            label="Rabat (jako ułamek dziesiętny np. 0.15 dla 15%)"
            name="rabat"
            type="number"
            inputProps={{ step: "0.01" }}
            value={formData.rabat}
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

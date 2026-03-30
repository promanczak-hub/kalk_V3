import { useState, useEffect, useCallback } from "react";
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
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  alpha
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import VisibilityIcon from "@mui/icons-material/Visibility";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import HistoryIcon from "@mui/icons-material/History";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import RefreshIcon from "@mui/icons-material/Refresh";

import { apiClient } from "../lib/apiClient";
import GenericTableEditor from "./GenericTableEditor";

// Map of tables with specialized UIs in ControlCenter.tsx
const SPECIALIZED_UI_MAP: Record<string, string> = {
  "samar_classes": "🗂️ Klasy SAMAR (Master)",
  "engines": "🏎️ Tabele Napędów",
  "tab_okres_final": "📉 TAB. OKRES FINAL",
  "samar_class_mileage_corrections": "🛣️ Korekty Przebiegowe",
  "samar_brand_corrections": "🏢 Korekty Marki/Modelu",
  "samar_service_costs": "🛠️ Koszty Serwisowe",
  "koszty_opon": "🛞 Tabela Opon",
  "replacement_car_rates": "🚗 Auto Zastępcze",
  "ltr_admin_ubezpieczenia": "🛡️ Stawki AC/OC",
  "ltr_admin_wspolczynniki_szkodowe": "💥 Współczynniki Szkodowe",
  "ltr_admin_oplaty_transportowe": "🚚 Opłaty Transportowe",
  "tabela_rabaty": "💰 Tabele Rabatów"
};

export default function DatabaseRegistryPanel() {
  const [registry, setRegistry] = useState<Record<string, string>>({});
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);

  const fetchRegistry = useCallback(async () => {
    try {
      const res = await apiClient.fetch("/api/config/registry");
      if (res.ok) {
        const data = await res.json();
        setRegistry(data);
      }
    } catch (err) {
      console.error("Failed to fetch registry:", err);
    }
  }, []);

  useEffect(() => {
    fetchRegistry();
  }, [fetchRegistry]);

  const handleExportXlsx = (tableName: string) => {
    window.open(`/api/config/${tableName}/export-xlsx`, "_blank");
  };

  const filteredTables = Object.entries(registry)
    .filter(([id, label]) => 
      id.toLowerCase().includes(searchTerm.toLowerCase()) || 
      label.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => a[1].localeCompare(b[1]));

  return (
    <Box>
      <Paper sx={{ p: 2, mb: 3, borderRadius: 2, bgcolor: alpha("#1976d2", 0.05) }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h6" color="primary">🗄️ Rejestr Baz Danych (Audit 1:1)</Typography>
          <Box sx={{ display: "flex", gap: 1 }}>
            <TextField
              size="small"
              placeholder="Szukaj tabeli..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: <SearchIcon fontSize="small" sx={{ mr: 1, color: "text.secondary" }} />,
              }}
              sx={{ width: 300 }}
            />
            <IconButton onClick={fetchRegistry} size="small">
              <RefreshIcon />
            </IconButton>
          </Box>
        </Box>
        <Typography variant="body2" color="text.secondary">
          Poniżej znajduje się pełna lista tabel konfiguracyjnych systemu whitelisted w backendzie.
          Każda tabela jest dostępna do edycji via Grid lub XLSX.
        </Typography>
      </Paper>

      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: "bold", bgcolor: "grey.50" }}>Nazwa Przyjazna</TableCell>
              <TableCell sx={{ fontWeight: "bold", bgcolor: "grey.50" }}>ID Tabeli (Online DB)</TableCell>
              <TableCell sx={{ fontWeight: "bold", bgcolor: "grey.50" }}>Dedykowany Panel</TableCell>
              <TableCell sx={{ fontWeight: "bold", bgcolor: "grey.50" }} align="right">Akcje</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredTables.map(([id, label]) => {
              const specializedTab = SPECIALIZED_UI_MAP[id];
              return (
                <TableRow key={id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight={600}>{label}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" sx={{ fontFamily: "monospace" }}>{id}</Typography>
                  </TableCell>
                  <TableCell>
                    {specializedTab ? (
                      <Chip 
                        size="small" 
                        label={specializedTab} 
                        color="info" 
                        variant="outlined" 
                        icon={<OpenInNewIcon sx={{ fontSize: "12px !important" }} />}
                      />
                    ) : (
                      <Chip size="small" label="Tylko Rejestr" color="default" variant="outlined" />
                    )}
                  </TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1 }}>
                      <Tooltip title="Otwórz Edytor (Audit)">
                        <IconButton size="small" color="primary" onClick={() => {
                          setSelectedTable(id);
                          setEditorOpen(true);
                        }}>
                          <VisibilityIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Pobierz XLSX (Control Copy)">
                        <IconButton size="small" color="success" onClick={() => handleExportXlsx(id)}>
                          <FileDownloadIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Historia Wersji / Snapshoty">
                        <IconButton size="small" color="secondary">
                          <HistoryIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Generic Editor Modal */}
      <Dialog 
        open={editorOpen} 
        onClose={() => setEditorOpen(false)} 
        maxWidth="lg" 
        fullWidth
        PaperProps={{ sx: { borderRadius: 3, height: '90vh' } }}
      >
        <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          Zapytanie 1:1 → {registry[selectedTable || ""] || selectedTable}
          <Typography variant="caption" sx={{ fontFamily: "monospace", ml: 2, color: 'text.secondary' }}>
            [{selectedTable}]
          </Typography>
        </DialogTitle>
        <DialogContent dividers sx={{ p: 0 }}>
          {selectedTable && <GenericTableEditor tableName={selectedTable} />}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditorOpen(false)}>Zamknij</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

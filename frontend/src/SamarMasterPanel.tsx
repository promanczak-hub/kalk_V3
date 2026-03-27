import { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Paper,
  alpha,
  useTheme,

  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import { apiClient } from './lib/apiClient';

interface SamarClass {
  id: number;
  name: string;
  base_mileage_km?: number;
  mileage_threshold_km?: number;
  base_period_months?: number;
  excel_code?: string;
  samar_class_id?: number;
  category?: string;
  size_class?: string;
  example_models?: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  Podstawowa: "#1976d2",
  "Sportowo-rekreacyjne": "#e91e63",
  "Terenowo-rekreacyjne (SUV)": "#4caf50",
  Vany: "#ff9800",
  Kombivany: "#9c27b0",
  Minibusy: "#00897b",
  "LEKKIE DOSTAWCZE": "#795548",
  "PICK-UP": "#bf360c",
  "ŚREDNIE DOSTAWCZE": "#5d4037",
  "CIĘŻKIE DOSTAWCZE": "#37474f",
  AUTOBUSY: "#006064",
};

/* ─────────── Master Table View ─────────── */
function MasterTableView({ classes }: { classes: SamarClass[] }) {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";

  // Sort by ID to mimic the exact 1-33 list from the spreadsheet
  const sortedClasses = [...classes].sort((a, b) => a.id - b.id);

  return (
    <Box>
      <Paper
        elevation={0}
        sx={{
          p: 2,
          mb: 2,
          borderRadius: 2,
          bgcolor: isDark ? alpha("#0d47a1", 0.08) : alpha("#e3f2fd", 0.5),
          border: `1px solid ${isDark ? "#1565c0" : "#90caf9"}`,
        }}
      >
        <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5, display: "flex", alignItems: "center", gap: 1 }}>
          🗂️ SAMAR Master Table — Baza Danych (CRUD)
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          Poniższa tabela odzwierciedla główny arkusz klas. Klucz ID (1-33) to fundament kalkulacyjny dla wszystkich pozostałych zakładek (Ubezpieczenia, Serwis, Napędy).
        </Typography>
      </Paper>

      <TableContainer component={Paper} elevation={0} sx={{ maxHeight: '70vh', border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
        <Table stickyHeader size="small" sx={{ 
          '& .MuiTableCell-root': { 
            borderRight: '1px solid', 
            borderColor: 'divider',
            padding: '6px 16px'
          } 
        }}>
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 800, width: 60, bgcolor: isDark ? 'grey.900' : 'grey.100' }}>ID</TableCell>
              <TableCell sx={{ fontWeight: 800, width: 220, bgcolor: isDark ? 'grey.900' : 'grey.100' }}>Kategoria</TableCell>
              <TableCell sx={{ fontWeight: 800, width: 200, bgcolor: isDark ? 'grey.900' : 'grey.100' }}>Segment</TableCell>
              <TableCell sx={{ fontWeight: 800, minWidth: 250, bgcolor: isDark ? 'grey.900' : 'grey.100' }}>Pełna nazwa klasy</TableCell>
              <TableCell sx={{ fontWeight: 800, minWidth: 350, bgcolor: isDark ? 'grey.900' : 'grey.100' }}>Przykładowe modele</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sortedClasses.map((cls) => {
              const catUpper = (cls.category || "INNE").toUpperCase();
              const catColor = CATEGORY_COLORS[cls.category || "INNE"] || CATEGORY_COLORS[catUpper] || "#757575";
              
              return (
                <TableRow 
                  key={cls.id} 
                  hover
                  sx={{ '&:last-child td, &:last-child th': { borderBottom: 0 } }}
                >
                  <TableCell sx={{ 
                    fontWeight: 700, 
                    fontSize: '0.85rem', 
                    bgcolor: alpha(catColor, 0.1), 
                    color: isDark ? catColor : 'inherit', 
                    borderRight: `3px solid ${catColor} !important` 
                  }}>
                    {cls.id}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 600, fontSize: '0.75rem', color: catColor }}>
                    {catUpper}
                  </TableCell>
                  <TableCell sx={{ fontSize: '0.75rem' }}>{cls.size_class || "—"}</TableCell>
                  <TableCell sx={{ fontWeight: 600, fontSize: '0.8rem' }}>{cls.name}</TableCell>
                  <TableCell sx={{ 
                    fontSize: '0.75rem', 
                    color: 'text.secondary',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    maxWidth: 400
                  }} title={cls.example_models || ""}>
                    {cls.example_models || "—"}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}



/* ─────────── Main Panel ─────────── */
export default function SamarMasterPanel() {
  const [classes, setClasses] = useState<SamarClass[]>([]);

  useEffect(() => {
    apiClient.fetch(`/api/samar-classes`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Błąd HTTP: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        if (Array.isArray(data)) {
          setClasses(data);
        } else {
          console.error("Oczekiwano tablicy, otrzymano:", data);
        }
      })
      .catch((err) => {
        console.error("Błąd pobierania klas SAMAR:", err);
      });
  }, []);

  return (
    <Box>
      <MasterTableView classes={classes} />
    </Box>
  );
}

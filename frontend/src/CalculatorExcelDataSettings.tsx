import { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Paper,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TableContainer
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import axios from "axios";

interface CalculatorExcelData {
  id?: string;
  sheet_name: string;
  row_data: Record<string, unknown>[];
  updated_at?: string;
}

export default function CalculatorExcelDataSettings() {
  const [data, setData] = useState<CalculatorExcelData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await axios.get("http://127.0.0.1:8000/api/calculator-excel-data");
      setData(res.data);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Nieznany błąd";
      setError(errorMessage || "Błąd podczas pobierania danych z bazy.");
    } finally {
      setLoading(false);
    }
  };

  if (loading && data.length === 0) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 5 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 3 }}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" color="primary" fontWeight="bold" gutterBottom>
          Digital Twin (Dane z Excela)
        </Typography>
        <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
          Poniżej znajdują się dane zaimportowane z pliku Excel bez przetwarzania. Są używane przez algorytm wyceny.
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        {data.map((sheet, index) => {
          // Pobierz nagłówki z pierwszego wiersza
          const headers = sheet.row_data.length > 0 ? Object.keys(sheet.row_data[0]) : [];

          return (
            <Accordion key={index} defaultExpanded={index === 0}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography fontWeight="bold" color="primary">
                  Arkusz: {sheet.sheet_name} ({sheet.row_data.length} rekordów)
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <TableContainer component={Box} sx={{ maxHeight: 400, overflow: 'auto' }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        {headers.map((h) => (
                          <TableCell key={h} sx={{ fontWeight: 'bold', bgcolor: '#f5f5f5' }}>{h}</TableCell>
                        ))}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {sheet.row_data.map((row, rIndex) => (
                        <TableRow key={rIndex}>
                          {headers.map((h) => (
                            <TableCell key={h}>{String(row[h] ?? "")}</TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </AccordionDetails>
            </Accordion>
          );
        })}
      </Paper>
    </Box>
  );
}

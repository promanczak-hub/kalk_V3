import { useState, useEffect } from "react";
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
  Chip,
  Button,
} from "@mui/material";
import axios from "axios";

interface KalkulacjaRow {
  id: string;
  numer_kalkulacji: string;
  status: string;
  dane_pojazdu: string;
  cena_netto: number;
  created_at: string;
}

export default function KalkulacjeList() {
  const [rows, setRows] = useState<KalkulacjaRow[]>([]);

  const fetchKalkulacje = async () => {
    try {
      const res = await axios.get("http://127.0.0.1:8000/api/kalkulacje");
      setRows(res.data);
    } catch (e) {
      console.error("Failed to fetch kalkulacje", e);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchKalkulacje();
  }, []);

  const handleOpen = (id: string) => {
    const params = new URLSearchParams();
    params.set('id', id);
    window.dispatchEvent(
      new CustomEvent('switchTab', {
        detail: { tabIndex: 2, urlParams: params },
      })
    );
  };

  return (
    <Box>
      <Typography
        variant="h5"
        color="primary"
        sx={{ mb: 3, fontWeight: "bold" }}
      >
        Oczekujące Kalkulacje (Platforma VertexExtractor)
      </Typography>
      <TableContainer
        component={Paper}
        variant="outlined"
        sx={{ borderRadius: 2 }}
      >
        <Table sx={{ minWidth: 650 }}>
          <TableHead sx={{ backgroundColor: "#f8fafc" }}>
            <TableRow>
              <TableCell sx={{ fontWeight: "bold" }}>
                Numer Kalkulacji
              </TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Pojazd</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Cena Netto</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Status</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Data Wpływu</TableCell>
              <TableCell sx={{ fontWeight: "bold" }} align="right">
                Akcje
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => (
              <TableRow 
                key={row.id} 
                hover 
                onClick={() => handleOpen(row.id)} // Allow single click to act as preview or same as double click for now? The user requested double-click specifically, let's use onDoubleClick
                onDoubleClick={() => handleOpen(row.id)}
                sx={{ cursor: "pointer" }}
              >
                <TableCell sx={{ fontWeight: "medium" }}>
                  {row.numer_kalkulacji}
                </TableCell>
                <TableCell>{row.dane_pojazdu}</TableCell>
                <TableCell>
                  {row.cena_netto?.toLocaleString("pl-PL", {
                    style: "currency",
                    currency: "PLN",
                  })}
                </TableCell>
                <TableCell>
                  <Chip
                    label={
                      row.status === "szkic_vertex"
                        ? "Szkic z Vertex"
                        : row.status
                    }
                    color={row.status === "szkic_vertex" ? "info" : "default"}
                    size="small"
                    sx={{ fontWeight: "medium" }}
                  />
                </TableCell>
                <TableCell>
                  {new Date(row.created_at).toLocaleString("pl-PL", {
                    year: "numeric",
                    month: "2-digit",
                    day: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </TableCell>
                <TableCell align="right">
                  <Button
                    variant="contained"
                    size="small"
                    color="primary"
                    onClick={(e) => {
                      e.stopPropagation(); // prevent row double-click logic from firing twice if fast clicked
                      handleOpen(row.id);
                    }}
                    sx={{ borderRadius: 2 }}
                  >
                    Opracuj Ofertę
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {rows.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={6}
                  align="center"
                  sx={{ py: 6, color: "text.secondary" }}
                >
                  <Typography variant="body1">
                    Brak oczekujących ofert.
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    Zleć parseowanie nowej oferty PDF w aplikacji
                    VertexExtractor.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

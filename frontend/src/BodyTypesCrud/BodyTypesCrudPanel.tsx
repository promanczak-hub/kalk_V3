import { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Chip,
  Alert,
} from "@mui/material";
import { API_BASE_URL } from "../config/env";
import { apiClient } from "../lib/apiClient";

const BASE_URL = API_BASE_URL;

const VEHICLE_CLASSES = ["Osobowy", "Ciężarowy"] as const;

interface BodyTypeItem {
  id?: number;
  nazwa_nadwozia: string;
  typ_pojazdu: string;
  utrata_wartosci?: number;
}

function getClassColor(vc: string): "primary" | "warning" | "default" {
  if (vc === "Osobowy") return "primary";
  if (vc === "Ciężarowy") return "warning";
  return "default";
}

export default function BodyTypesCrudPanel() {
  const [data, setData] = useState<BodyTypeItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const resp = await apiClient.fetch(`${BASE_URL}/api/body-types`);
      if (resp.ok) {
        const json = await resp.json();
        if (Array.isArray(json)) setData(json);
      }
    } catch (e) {
      console.error("Failed to load body types:", e);
    } finally {
      setLoading(false);
    }
  };

  const grouped = VEHICLE_CLASSES.map((vc) => ({
    label: vc,
    items: data.filter((d) => d.typ_pojazdu === vc),
  }));

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 1 }}>
        Słownik Typów Nadwozia
      </Typography>
      <Alert severity="info" sx={{ mb: 2 }}>
        SOT: Google Sheet <code>body_types</code> (gid=484265370). Edycja w GSheet,
        synchronizacja przez <code>backend/scripts/sync_body_types.py</code>.
      </Alert>
      {loading ? (
        <CircularProgress />
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead sx={{ backgroundColor: "#f8fafc" }}>
              <TableRow>
                <TableCell>Typ Nadwozia</TableCell>
                <TableCell>Kategoria</TableCell>
                <TableCell align="right">Korekta WR</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {grouped.map((group) => [
                <TableRow key={`header-${group.label}`}>
                  <TableCell
                    colSpan={3}
                    sx={{
                      bgcolor: "rgba(0,0,0,0.04)",
                      fontWeight: 700,
                      fontSize: "0.8rem",
                    }}
                  >
                    {group.label === "Osobowy" ? "🚗" : "🚛"} {group.label} (
                    {group.items.length})
                  </TableCell>
                </TableRow>,
                ...group.items.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell sx={{ fontWeight: 500, pl: 4 }}>
                      {row.nazwa_nadwozia}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={row.typ_pojazdu}
                        size="small"
                        color={getClassColor(row.typ_pojazdu)}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="right">
                      {((row.utrata_wartosci ?? 0) * 100).toFixed(2)}%
                    </TableCell>
                  </TableRow>
                )),
              ])}
              {data.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={3}
                    align="center"
                    sx={{ py: 3, color: "text.secondary" }}
                  >
                    Brak zdefiniowanych typów nadwozia.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}

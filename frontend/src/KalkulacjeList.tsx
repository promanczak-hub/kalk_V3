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
  Chip,
  Button,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Select,
  Tooltip,
} from "@mui/material";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import axios from "axios";

/* ── Types ── */

interface KalkulacjaRow {
  id: string;
  numer_kalkulacji: string;
  status: string;
  dane_pojazdu: string | null;
  cena_netto: number | null;
  created_at: string;
  updated_at: string;
  body_type: string | null;
  fuel_type: string | null;
  discount_pct: number | null;
  options_count: number;
}

/* ── Helpers ── */

const STATUS_MAP: Record<string, { label: string; color: "info" | "warning" | "success" | "secondary" | "default" }> = {
  szkic_vertex: { label: "Szkic z Vertex", color: "info" },
  w_opracowaniu: { label: "W opracowaniu", color: "warning" },
  gotowa: { label: "Gotowa", color: "success" },
  wyslana: { label: "Wysłana", color: "secondary" },
  archiwum: { label: "Archiwum", color: "default" },
};

const FUEL_ICON: Record<string, string> = {
  diesel: "⛽",
  benzyna: "⛽",
  elektryczny: "⚡",
  hybryda: "🔋",
  "plug-in hybrid": "🔌",
};

function fuelIcon(fuel: string | null): string {
  if (!fuel) return "—";
  const key = fuel.toLowerCase().trim();
  for (const [k, icon] of Object.entries(FUEL_ICON)) {
    if (key.includes(k)) return icon;
  }
  return "⛽";
}

/* ── Component ── */

export default function KalkulacjeList() {
  const [rows, setRows] = useState<KalkulacjaRow[]>([]);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [menuRowId, setMenuRowId] = useState<string | null>(null);

  const fetchKalkulacje = useCallback(async () => {
    try {
      const res = await axios.get("http://127.0.0.1:8000/api/kalkulacje");
      setRows(res.data);
    } catch (e) {
      console.error("Failed to fetch kalkulacje", e);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchKalkulacje();
  }, [fetchKalkulacje]);

  /* ── Navigation ── */
  const handleOpen = (id: string) => {
    const params = new URLSearchParams();
    params.set("id", id);
    window.dispatchEvent(
      new CustomEvent("switchTab", {
        detail: { tabIndex: 2, urlParams: params },
      })
    );
  };

  /* ── Actions ── */
  const handleMenuOpen = (e: React.MouseEvent<HTMLElement>, rowId: string) => {
    e.stopPropagation();
    setMenuAnchor(e.currentTarget);
    setMenuRowId(rowId);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
    setMenuRowId(null);
  };

  const handleDuplicate = async () => {
    if (!menuRowId) return;
    handleMenuClose();
    try {
      await axios.post(`http://127.0.0.1:8000/api/kalkulacje/${menuRowId}/duplicate`);
      await fetchKalkulacje();
    } catch (e) {
      console.error("Duplicate failed", e);
      alert("Nie udało się zduplikować kalkulacji.");
    }
  };

  const handleDelete = async () => {
    if (!menuRowId) return;
    const confirmed = window.confirm("Czy na pewno chcesz usunąć tę kalkulację?");
    if (!confirmed) {
      handleMenuClose();
      return;
    }
    handleMenuClose();
    try {
      await axios.delete(`http://127.0.0.1:8000/api/kalkulacje/${menuRowId}`);
      setRows((prev) => prev.filter((r) => r.id !== menuRowId));
    } catch (e) {
      console.error("Delete failed", e);
      alert("Nie udało się usunąć kalkulacji.");
    }
  };

  const handleStatusChange = async (rowId: string, newStatus: string) => {
    try {
      await axios.patch(`http://127.0.0.1:8000/api/kalkulacje/${rowId}/status`, {
        status: newStatus,
      });
      setRows((prev) =>
        prev.map((r) => (r.id === rowId ? { ...r, status: newStatus } : r))
      );
    } catch (e) {
      console.error("Status update failed", e);
      alert("Nie udało się zmienić statusu.");
    }
  };

  /* ── Render ── */
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
        <Table sx={{ minWidth: 900 }} size="small">
          <TableHead sx={{ backgroundColor: "#f8fafc" }}>
            <TableRow>
              <TableCell sx={{ fontWeight: "bold" }}>Numer</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Pojazd</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Nadwozie</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Paliwo</TableCell>
              <TableCell sx={{ fontWeight: "bold" }} align="right">Rabat&nbsp;%</TableCell>
              <TableCell sx={{ fontWeight: "bold" }} align="right">Cena Netto</TableCell>
              <TableCell sx={{ fontWeight: "bold" }} align="center">Opcje</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Status</TableCell>
              <TableCell sx={{ fontWeight: "bold" }}>Data&nbsp;wpływu</TableCell>
              <TableCell sx={{ fontWeight: "bold" }} align="right">
                Akcje
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => {
              const statusMeta = STATUS_MAP[row.status] ?? {
                label: row.status,
                color: "default" as const,
              };
              return (
                <TableRow
                  key={row.id}
                  hover
                  onDoubleClick={() => handleOpen(row.id)}
                  sx={{ cursor: "pointer" }}
                >
                  {/* Numer */}
                  <TableCell sx={{ fontWeight: 500, fontSize: "0.8rem", whiteSpace: "nowrap" }}>
                    {row.numer_kalkulacji}
                  </TableCell>

                  {/* Pojazd */}
                  <TableCell sx={{ maxWidth: 220 }}>
                    <Typography
                      variant="body2"
                      sx={{ fontWeight: 600 }}
                      noWrap
                    >
                      {row.dane_pojazdu || "—"}
                    </Typography>
                  </TableCell>

                  {/* Nadwozie */}
                  <TableCell>
                    {row.body_type ? (
                      <Chip
                        label={row.body_type}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: "0.7rem" }}
                      />
                    ) : (
                      <Typography variant="caption" color="text.disabled">—</Typography>
                    )}
                  </TableCell>

                  {/* Paliwo */}
                  <TableCell>
                    <Tooltip title={row.fuel_type || "Brak danych"} arrow>
                      <span style={{ fontSize: "0.85rem" }}>
                        {fuelIcon(row.fuel_type)}{" "}
                        <span style={{ fontSize: "0.75rem" }}>
                          {row.fuel_type || "—"}
                        </span>
                      </span>
                    </Tooltip>
                  </TableCell>

                  {/* Rabat % */}
                  <TableCell align="right">
                    {row.discount_pct != null && row.discount_pct > 0 ? (
                      <Typography
                        variant="body2"
                        sx={{ color: "success.main", fontWeight: 600 }}
                      >
                        {row.discount_pct.toFixed(1)}%
                      </Typography>
                    ) : (
                      <Typography variant="caption" color="text.disabled">
                        —
                      </Typography>
                    )}
                  </TableCell>

                  {/* Cena Netto */}
                  <TableCell align="right">
                    {row.cena_netto != null && row.cena_netto > 0 ? (
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {row.cena_netto.toLocaleString("pl-PL", {
                          style: "currency",
                          currency: "PLN",
                          maximumFractionDigits: 0,
                        })}
                      </Typography>
                    ) : (
                      <Typography variant="caption" color="text.disabled">
                        0,00 zł
                      </Typography>
                    )}
                  </TableCell>

                  {/* Opcje count */}
                  <TableCell align="center">
                    {row.options_count > 0 ? (
                      <Chip
                        label={row.options_count}
                        size="small"
                        color="default"
                        sx={{ minWidth: 28, fontSize: "0.75rem" }}
                      />
                    ) : (
                      <Typography variant="caption" color="text.disabled">—</Typography>
                    )}
                  </TableCell>

                  {/* Status */}
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <Select
                      value={row.status}
                      onChange={(e) =>
                        handleStatusChange(row.id, e.target.value as string)
                      }
                      size="small"
                      variant="standard"
                      disableUnderline
                      sx={{ fontSize: "0.75rem" }}
                      renderValue={() => (
                        <Chip
                          label={statusMeta.label}
                          color={statusMeta.color}
                          size="small"
                          sx={{ fontWeight: 500, cursor: "pointer" }}
                        />
                      )}
                    >
                      {Object.entries(STATUS_MAP).map(([key, meta]) => (
                        <MenuItem key={key} value={key} dense>
                          <Chip
                            label={meta.label}
                            color={meta.color}
                            size="small"
                            sx={{ mr: 1 }}
                          />
                        </MenuItem>
                      ))}
                    </Select>
                  </TableCell>

                  {/* Data wpływu */}
                  <TableCell sx={{ whiteSpace: "nowrap", fontSize: "0.8rem" }}>
                    {new Date(row.created_at).toLocaleString("pl-PL", {
                      year: "numeric",
                      month: "2-digit",
                      day: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </TableCell>

                  {/* Akcje */}
                  <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                    <Button
                      variant="contained"
                      size="small"
                      color="primary"
                      startIcon={<OpenInNewIcon sx={{ fontSize: 16 }} />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpen(row.id);
                      }}
                      sx={{ borderRadius: 2, mr: 0.5, textTransform: "none", fontSize: "0.75rem" }}
                    >
                      Rozwiń
                    </Button>
                    <IconButton
                      size="small"
                      onClick={(e) => handleMenuOpen(e, row.id)}
                      sx={{ ml: 0.5 }}
                    >
                      <MoreVertIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              );
            })}
            {rows.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={10}
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

      {/* ⋮ Context Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
        anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
      >
        <MenuItem onClick={handleDuplicate} dense>
          <ListItemIcon>
            <ContentCopyIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Duplikuj</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleDelete} dense sx={{ color: "error.main" }}>
          <ListItemIcon>
            <DeleteOutlineIcon fontSize="small" color="error" />
          </ListItemIcon>
          <ListItemText>Usuń</ListItemText>
        </MenuItem>
      </Menu>
    </Box>
  );
}

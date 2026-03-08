import { useState, useCallback } from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  IconButton,
  Typography,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Chip,
  Tooltip,
  Snackbar,
  Divider,
} from '@mui/material';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import FileUploadIcon from '@mui/icons-material/FileUpload';
import HistoryIcon from '@mui/icons-material/History';
import SaveIcon from '@mui/icons-material/Save';
import RestoreIcon from '@mui/icons-material/Restore';
import DownloadIcon from '@mui/icons-material/Download';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface VersionInfo {
  id: number;
  table_name: string;
  version_num: number;
  label: string;
  created_at: string;
  created_by: string;
  row_count: number;
}

interface ImportReport {
  status: string;
  updated: number;
  inserted: number;
  skipped: number;
  errors: string[];
  snapshot_version: number | null;
}

interface Props {
  tableName: string;
  tableLabel: string;
  onDataChanged: () => void;
}

export default function ConfigTableToolbar({ tableName, tableLabel, onDataChanged }: Props) {
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' | 'info' }>({
    open: false, message: '', severity: 'info',
  });

  // Upload dialog
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [importReport, setImportReport] = useState<ImportReport | null>(null);

  // Version history dialog
  const [historyOpen, setHistoryOpen] = useState(false);
  const [versions, setVersions] = useState<VersionInfo[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);

  // Snapshot dialog
  const [snapshotOpen, setSnapshotOpen] = useState(false);
  const [snapshotLabel, setSnapshotLabel] = useState('');

  // ── Download XLSX ──
  const handleDownload = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/api/config/${tableName}/export-xlsx`);
      if (!resp.ok) throw new Error(await resp.text());
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${tableName}_export.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      setSnackbar({ open: true, message: '📥 Plik XLSX pobrany pomyślnie', severity: 'success' });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setSnackbar({ open: true, message: `Błąd pobierania: ${message}`, severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [tableName]);

  // ── Upload XLSX ──
  const handleUpload = useCallback(async () => {
    if (!uploadFile) return;
    setLoading(true);
    setImportReport(null);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      const resp = await fetch(`${API_BASE}/api/config/${tableName}/import-xlsx`, {
        method: 'POST',
        body: formData,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || resp.statusText);
      }
      const report: ImportReport = await resp.json();
      setImportReport(report);
      onDataChanged();
      setSnackbar({
        open: true,
        message: `✅ Import: ${report.updated} zaktualizowanych, ${report.inserted} nowych`,
        severity: 'success',
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setSnackbar({ open: true, message: `Błąd importu: ${message}`, severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [tableName, uploadFile, onDataChanged]);

  // ── Fetch versions ──
  const fetchVersions = useCallback(async () => {
    setVersionsLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/api/config/${tableName}/versions`);
      if (!resp.ok) throw new Error(await resp.text());
      const data: VersionInfo[] = await resp.json();
      setVersions(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setSnackbar({ open: true, message: `Błąd: ${message}`, severity: 'error' });
    } finally {
      setVersionsLoading(false);
    }
  }, [tableName]);

  // ── Create manual snapshot ──
  const handleSnapshot = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/api/config/${tableName}/snapshot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: snapshotLabel || 'Ręczny snapshot' }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const result = await resp.json();
      setSnackbar({
        open: true,
        message: `💾 Snapshot v${result.version_num} utworzony`,
        severity: 'success',
      });
      setSnapshotOpen(false);
      setSnapshotLabel('');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setSnackbar({ open: true, message: `Błąd: ${message}`, severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [tableName, snapshotLabel]);

  // ── Restore version ──
  const handleRestore = useCallback(async (versionId: number, versionNum: number) => {
    if (!window.confirm(`Przywrócić dane z wersji v${versionNum}? Obecne dane zostaną nadpisane (automatyczny backup zostanie utworzony).`)) return;
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/api/config/${tableName}/restore/${versionId}`, {
        method: 'POST',
      });
      if (!resp.ok) throw new Error(await resp.text());
      const result = await resp.json();
      setSnackbar({
        open: true,
        message: `🔄 Przywrócono v${result.restored_version} (${result.restored_rows} wierszy)`,
        severity: 'success',
      });
      onDataChanged();
      fetchVersions(); // Refresh version list
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setSnackbar({ open: true, message: `Błąd przywracania: ${message}`, severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [tableName, onDataChanged, fetchVersions]);

  // ── Download version XLSX ──
  const handleDownloadVersion = useCallback(async (versionId: number, versionNum: number) => {
    try {
      const resp = await fetch(`${API_BASE}/api/config/${tableName}/versions/${versionId}/export-xlsx`);
      if (!resp.ok) throw new Error(await resp.text());
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${tableName}_v${versionNum}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setSnackbar({ open: true, message: `Błąd: ${message}`, severity: 'error' });
    }
  }, [tableName]);

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString('pl-PL', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    } catch {
      return iso;
    }
  };

  return (
    <>
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
        <Button
          variant="outlined"
          size="small"
          startIcon={<FileDownloadIcon />}
          onClick={handleDownload}
          disabled={loading}
        >
          Pobierz XLSX
        </Button>

        <Button
          variant="outlined"
          size="small"
          startIcon={<FileUploadIcon />}
          onClick={() => { setUploadOpen(true); setImportReport(null); setUploadFile(null); }}
          disabled={loading}
        >
          Wgraj XLSX
        </Button>

        <Button
          variant="outlined"
          size="small"
          startIcon={<HistoryIcon />}
          onClick={() => { setHistoryOpen(true); fetchVersions(); }}
          disabled={loading}
        >
          Historia wersji
        </Button>

        <Button
          variant="outlined"
          size="small"
          startIcon={<SaveIcon />}
          onClick={() => setSnapshotOpen(true)}
          disabled={loading}
        >
          Zapisz wersję
        </Button>

        {loading && <CircularProgress size={20} />}
      </Box>

      {/* ── Upload Dialog ── */}
      <Dialog open={uploadOpen} onClose={() => setUploadOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>📤 Wgraj XLSX — {tableLabel}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
            Automatyczny backup zostanie utworzony przed importem.
            Edytuj tylko odblokowane komórki (dane). Nie zmieniaj nagłówków ani kolumny ID.
          </Typography>

          <Button variant="contained" component="label" sx={{ mb: 2 }}>
            Wybierz plik
            <input
              type="file"
              accept=".xlsx,.xls"
              hidden
              onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
            />
          </Button>

          {uploadFile && (
            <Typography variant="body2" sx={{ ml: 1, display: 'inline' }}>
              📄 {uploadFile.name}
            </Typography>
          )}

          {importReport && (
            <Box sx={{ mt: 2 }}>
              <Alert severity={importReport.errors.length > 0 ? 'warning' : 'success'} sx={{ mb: 1 }}>
                Zaktualizowano: <strong>{importReport.updated}</strong> |
                Dodano: <strong>{importReport.inserted}</strong> |
                Pominięto: <strong>{importReport.skipped}</strong>
                {importReport.snapshot_version && (
                  <> | Backup: v{importReport.snapshot_version}</>
                )}
              </Alert>
              {importReport.errors.length > 0 && (
                <Alert severity="error">
                  {importReport.errors.map((e, i) => <div key={i}>{e}</div>)}
                </Alert>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadOpen(false)}>Zamknij</Button>
          <Button
            variant="contained"
            onClick={handleUpload}
            disabled={!uploadFile || loading}
            startIcon={loading ? <CircularProgress size={16} /> : <FileUploadIcon />}
          >
            Importuj
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Version History Dialog ── */}
      <Dialog open={historyOpen} onClose={() => setHistoryOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>🕐 Historia wersji — {tableLabel}</DialogTitle>
        <DialogContent dividers>
          {versionsLoading ? (
            <Box display="flex" justifyContent="center" p={3}><CircularProgress /></Box>
          ) : versions.length === 0 ? (
            <Typography color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>
              Brak zapisanych wersji. Kliknij "Zapisz wersję" aby utworzyć pierwszą.
            </Typography>
          ) : (
            <List dense>
              {versions.map((v, idx) => (
                <Box key={v.id}>
                  <ListItem sx={{ py: 1 }}>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Chip label={`v${v.version_num}`} size="small" color="primary" variant="outlined" />
                          <Typography variant="body2" fontWeight={500}>
                            {v.label || 'Bez opisu'}
                          </Typography>
                        </Box>
                      }
                      secondary={`${formatDate(v.created_at)} • ${v.row_count} wierszy • ${v.created_by}`}
                    />
                    <ListItemSecondaryAction>
                      <Tooltip title="Pobierz XLSX tej wersji">
                        <IconButton size="small" onClick={() => handleDownloadVersion(v.id, v.version_num)}>
                          <DownloadIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Przywróć tę wersję">
                        <IconButton
                          size="small"
                          color="warning"
                          onClick={() => handleRestore(v.id, v.version_num)}
                          disabled={loading}
                        >
                          <RestoreIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </ListItemSecondaryAction>
                  </ListItem>
                  {idx < versions.length - 1 && <Divider />}
                </Box>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHistoryOpen(false)}>Zamknij</Button>
        </DialogActions>
      </Dialog>

      {/* ── Snapshot Dialog ── */}
      <Dialog open={snapshotOpen} onClose={() => setSnapshotOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>💾 Zapisz wersję — {tableLabel}</DialogTitle>
        <DialogContent>
          <TextField
            label="Opis wersji (opcjonalny)"
            placeholder="np. Przed aktualizacją Q2 2026"
            fullWidth
            value={snapshotLabel}
            onChange={(e) => setSnapshotLabel(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSnapshotOpen(false)}>Anuluj</Button>
          <Button
            variant="contained"
            onClick={handleSnapshot}
            disabled={loading}
            startIcon={loading ? <CircularProgress size={16} /> : <SaveIcon />}
          >
            Zapisz
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Snackbar ── */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={5000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          severity={snackbar.severity}
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          variant="filled"
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  );
}

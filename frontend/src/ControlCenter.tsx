import { useState, useEffect } from 'react';
import { 
  Box, Typography, Paper, Grid, Button, TextField, Divider, Dialog, DialogTitle, 
  DialogContent, CircularProgress, Alert, Accordion, AccordionSummary, AccordionDetails,
  Table, TableBody, TableCell, TableHead, TableRow, Tabs, Tab, Switch, FormControlLabel
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { SAMAR_MARKDOWN } from './samar_markdown';
import SamarRVPanel from './SamarRVPanel';

interface TyreCost {
  id?: string;
  tyre_class: string;
  diameter: number;
  purchase_price: number;
  buyback_price: number;
}

interface ControlCenterSettings {
  default_wibor: number;
  default_ltr_margin: number;
  bank_spread: number;
  samar_segment_b_adjustment: number;
  samar_segment_c_adjustment: number;
  samar_segment_d_adjustment: number;
  value_threshold_1: number;
  value_threshold_2: number;
  resale_time_days: number;
  inventory_financing_cost: number;
  samar_rv_apply_color_correction: boolean;
  samar_rv_apply_body_correction: boolean;
  samar_rv_apply_options_depreciation: boolean;
  samar_rv_base_mileage: number;
  samar_rv_mileage_unit_km: number;

  // Koszty Dodatkowe
  cost_gsm_subscription_monthly: number;
  cost_gsm_device: number;
  cost_gsm_installation: number;
  cost_hook_installation: number;
  cost_grid_dismantling: number;
  cost_registration: number;
  cost_sales_prep: number;
}

export default function ControlCenter() {
  const [settings, setSettings] = useState<ControlCenterSettings | null>(null);
  const [tyreCosts, setTyreCosts] = useState<TyreCost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await axios.get<ControlCenterSettings>('http://127.0.0.1:8000/api/control-center');
      setSettings(response.data);
      
      const tyreResp = await axios.get<TyreCost[]>('http://127.0.0.1:8000/api/tyre-costs');
      setTyreCosts(tyreResp.data);

      setError(null);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Nieznany błąd';
      setError(errorMessage || 'Błąd ładowania ustawień. Zobacz konsolę w celu zdiagnozowania.');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!settings) return;
    setLoading(true);
    try {
      await axios.post('http://127.0.0.1:8000/api/control-center', settings);
      setSuccessMsg('Zapisano ustawienia pomyślnie na serwerze i w bazie docelowej!');
      setTimeout(() => setSuccessMsg(null), 3000);
      setError(null);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Nieznany błąd';
      setError(errorMessage || 'Błąd polecenia zapisu');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field: keyof ControlCenterSettings, value: string | boolean) => {
    if (!settings) return;
    setSettings({ ...settings, [field]: typeof value === 'boolean' ? value : Number(value) });
  };

  const handleAddTyreCost = () => {
    setTyreCosts([...tyreCosts, { tyre_class: '', diameter: 15, purchase_price: 0.0, buyback_price: 0.0 }]);
  };

  const handleUpdateTyreCost = (index: number, field: keyof TyreCost, value: string | number) => {
    const updated = [...tyreCosts];
    updated[index] = { ...updated[index], [field]: value };
    setTyreCosts(updated);
  };

  const handleSaveTyreCost = async (index: number) => {
    const cost = tyreCosts[index];
    if (!cost.tyre_class || cost.diameter == null || cost.purchase_price == null || cost.buyback_price == null) {
       setError("Klasa, średnica i ceny są wymagane.");
       return;
    }
    setLoading(true);
    try {
      const res = await axios.post('http://127.0.0.1:8000/api/tyre-costs', cost);
      const updated = [...tyreCosts];
      updated[index] = res.data;
      setTyreCosts(updated);
      setSuccessMsg('Zapisano koszt opony pomyślnie!');
      setTimeout(() => setSuccessMsg(null), 3000);
      setError(null);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Nieznany błąd';
      setError(errorMessage || 'Błąd zapisu kosztu opony');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTyreCost = async (index: number) => {
    const cost = tyreCosts[index];
    if (cost.id) {
       setLoading(true);
       try {
         await axios.delete(`http://127.0.0.1:8000/api/tyre-costs/${cost.id}`);
         setSuccessMsg('Usunięto koszt opony!');
         setTimeout(() => setSuccessMsg(null), 3000);
       } catch {
         setError('Błąd usuwania kosztu opony');
         setLoading(false);
         return;
       }
       setLoading(false);
    }
    const updated = [...tyreCosts];
    updated.splice(index, 1);
    setTyreCosts(updated);
  };

  if (loading && !settings) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 5 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs value={activeTab} onChange={(_e, val) => setActiveTab(val)}>
          <Tab label="Parametry Globalne i Opony" />
          <Tab label="Macierz Utraty Wartości (SAMAR)" />
        </Tabs>
      </Box>

      {activeTab === 0 && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h5" color="primary" fontWeight="bold">
              Ustawienia Finansowe i Flotowe
            </Typography>
            <Button variant="contained" color="primary" onClick={handleSave} disabled={loading}>
              {loading ? <CircularProgress size={24} /> : 'Zapisz ustawienia'}
            </Button>
          </Box>

      {error && <Alert severity="error">{error}</Alert>}
      {successMsg && <Alert severity="success">{successMsg}</Alert>}

      {settings && (
        <Grid container spacing={3}>
          {/* Wiersz 1: Kolumna lewa - Finanse i Marże */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper sx={{ p: 3, height: '100%' }} elevation={1}>
              <Typography variant="h6" color="primary" fontWeight="bold" gutterBottom>
                Parametry Finansowe
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <Grid container spacing={2} alignItems="center">
                <Grid size={{ xs: 6 }}><Typography variant="body2">Bazowa Stopa Procentowa (WIBOR)</Typography></Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth size="small" type="number" 
                    value={settings.default_wibor} onChange={(e) => handleChange('default_wibor', e.target.value)} />
                </Grid>

                <Grid size={{ xs: 6 }}><Typography variant="body2">Marża Finansowa (%)</Typography></Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth size="small" type="number" 
                    value={settings.default_ltr_margin} onChange={(e) => handleChange('default_ltr_margin', e.target.value)} />
                </Grid>
                
                <Grid size={{ xs: 6 }}><Typography variant="body2">Spread Bankowy (%)</Typography></Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth size="small" type="number" 
                    value={settings.bank_spread} onChange={(e) => handleChange('bank_spread', e.target.value)} />
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          {/* Wiersz 1: Kolumna prawa - Ustawienia Flotowe / SAMAR */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper sx={{ p: 3, height: '100%' }} elevation={1}>
              <Typography variant="h6" color="primary" fontWeight="bold" gutterBottom>
                Ustawienia Pojazdów (Klasyfikacja SAMAR)
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                Domyślny narzut na utratę wartości w zależności od segmentu (override klasyfikacji).
              </Typography>
              
              <Grid container spacing={2} alignItems="center">
                <Grid size={{ xs: 6 }}><Typography variant="body2">Segment B (Auta miejskie)</Typography></Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth size="small" type="number" label="Korekta WR %" 
                    value={settings.samar_segment_b_adjustment} onChange={(e) => handleChange('samar_segment_b_adjustment', e.target.value)} />
                </Grid>

                <Grid size={{ xs: 6 }}><Typography variant="body2">Segment C (Kompakty)</Typography></Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth size="small" type="number" label="Korekta WR %" 
                    value={settings.samar_segment_c_adjustment} onChange={(e) => handleChange('samar_segment_c_adjustment', e.target.value)} />
                </Grid>

                <Grid size={{ xs: 6 }}><Typography variant="body2">Segment D (Klasa Średnia)</Typography></Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth size="small" type="number" label="Korekta WR %" 
                    value={settings.samar_segment_d_adjustment} onChange={(e) => handleChange('samar_segment_d_adjustment', e.target.value)} />
                </Grid>
              </Grid>
              
              <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
                 <Button size="small" variant="outlined" color="primary" onClick={() => setModalOpen(true)}>
                   Macierz Segmentacji SAMAR
                 </Button>
              </Box>
            </Paper>
          </Grid>

          {/* Wiersz Dodatkowy: Kolumna lewa - Przełączniki SAMAR */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper sx={{ p: 3, height: '100%' }} elevation={1}>
              <Typography variant="h6" color="primary" fontWeight="bold" gutterBottom>
                Konfiguracja Algorytmu SAMAR
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                Główne przełączniki włączające kaskadowe kroki wg. V1 kalkulatora.
              </Typography>
              
              <Grid container spacing={2} flexDirection="column">
                <Grid size={{ xs: 12 }}>
                  <FormControlLabel
                    control={<Switch checked={settings.samar_rv_apply_color_correction} onChange={(e) => handleChange('samar_rv_apply_color_correction', e.target.checked)} />}
                    label="Uwzględniaj korektę koloru nadwozia (np. dopłata z Tabeli)"
                  />
                </Grid>
                <Grid size={{ xs: 12 }}>
                  <FormControlLabel
                    control={<Switch checked={settings.samar_rv_apply_body_correction} onChange={(e) => handleChange('samar_rv_apply_body_correction', e.target.checked)} />}
                    label="Uwzględniaj korektę rodzaju zabudowy (Furgon, Skrzynia)"
                  />
                </Grid>
                <Grid size={{ xs: 12 }}>
                  <FormControlLabel
                    control={<Switch checked={settings.samar_rv_apply_options_depreciation} onChange={(e) => handleChange('samar_rv_apply_options_depreciation', e.target.checked)} />}
                    label="Obliczaj deprecjację opcji fabrycznych (włączone w bazie Z Opcjami)"
                  />
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          {/* Wiersz Dodatkowy: Kolumna prawa - Limit Przebiegów SAMAR */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper sx={{ p: 3, height: '100%' }} elevation={1}>
              <Typography variant="h6" color="primary" fontWeight="bold" gutterBottom>
                Bazy Przebiegów SAMAR
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                Definicja, od której liczone są limity. V1 używał sztywno 140 000 km potrącając nadwyżki per 10 000 km.
              </Typography>
              
              <Grid container spacing={2} alignItems="center">
                <Grid size={{ xs: 6 }}><Typography variant="body2">Bazowy limit (Normatywny) [km]</Typography></Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth size="small" type="number" 
                    value={settings.samar_rv_base_mileage} onChange={(e) => handleChange('samar_rv_base_mileage', e.target.value)} />
                </Grid>

                <Grid size={{ xs: 6 }}><Typography variant="body2">Interwał skokowy naliczania [km]</Typography></Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth size="small" type="number" 
                    value={settings.samar_rv_mileage_unit_km} onChange={(e) => handleChange('samar_rv_mileage_unit_km', e.target.value)} />
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          {/* Wiersz 2: Kolumna lewa - Progi Wartościowe */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper sx={{ p: 3, height: '100%' }} elevation={1}>
              <Typography variant="h6" color="primary" fontWeight="bold" gutterBottom>
                Progi Wartościowe (Zależności Pojazdów)
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                Limity i pułapy kwotowe warunkujące specjalne przeliczenia bądź kategorie podatkowe / amortyzacyjne.
              </Typography>
              
              <Grid container spacing={2} alignItems="center">
                <Grid size={{ xs: 6 }}><Typography variant="body2">Próg Wartości 1 (niskie kwoty) [PLN]</Typography></Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth size="small" type="number" 
                    value={settings.value_threshold_1} onChange={(e) => handleChange('value_threshold_1', e.target.value)} />
                </Grid>

                <Grid size={{ xs: 6 }}><Typography variant="body2">Próg Wartości 2 (wysokie kwoty) [PLN]</Typography></Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth size="small" type="number" 
                    value={settings.value_threshold_2} onChange={(e) => handleChange('value_threshold_2', e.target.value)} />
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          {/* Wiersz 2: Kolumna prawa - Remarketing / Odsprzedaż */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper sx={{ p: 3, height: '100%' }} elevation={1}>
              <Typography variant="h6" color="primary" fontWeight="bold" gutterBottom>
                Proces Odsprzedaży (Remarketing)
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                Ustawienia sterujące czasem i obciążeniem kapitałowym odłożonym na okres odsprzedaży i stoku po-kontraktowego.
              </Typography>
              
              <Grid container spacing={2} alignItems="center">
                <Grid size={{ xs: 6 }}><Typography variant="body2">Średni czas na odsprzedaż (dni)</Typography></Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth size="small" type="number" 
                    value={settings.resale_time_days} onChange={(e) => handleChange('resale_time_days', e.target.value)} />
                </Grid>

                <Grid size={{ xs: 6 }}><Typography variant="body2">Koszt finansowania zapasu (%)</Typography></Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField fullWidth size="small" type="number" 
                    value={settings.inventory_financing_cost} onChange={(e) => handleChange('inventory_financing_cost', e.target.value)} />
                </Grid>
              </Grid>
            </Paper>
          </Grid>
          
          {/* Wiersz Dodatkowy: Kolumna Koszty Dodatkowe */}
          <Grid size={{ xs: 12 }}>
            <Paper sx={{ p: 3, height: '100%' }} elevation={1}>
              <Typography variant="h6" color="primary" fontWeight="bold" gutterBottom>
                Koszty Dodatkowe (Ryczałty - GPS, Hak, Rejestracja)
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                Koszty operacyjne doliczane miesięcznie do bazowej renty w wariancie wyceny (jeśli włączone w opcjach).
              </Typography>
              
              <Grid container spacing={3}>
                <Grid size={{ xs: 12, md: 4 }}>
                   <Typography variant="subtitle2" color="primary" gutterBottom>Urządzenie GPS (Abonament / Zakup / Montaż)</Typography>
                   <Divider sx={{ mb: 1 }} />
                   <Grid container spacing={2} alignItems="center">
                     <Grid size={{ xs: 8 }}><Typography variant="body2">Abonament GSM (miesięcznie)</Typography></Grid>
                     <Grid size={{ xs: 4 }}>
                        <TextField fullWidth size="small" type="number" 
                          value={settings.cost_gsm_subscription_monthly} onChange={(e) => handleChange('cost_gsm_subscription_monthly', e.target.value)} />
                     </Grid>
                     <Grid size={{ xs: 8 }}><Typography variant="body2">Cena Urządzenia GPS (zakup)</Typography></Grid>
                     <Grid size={{ xs: 4 }}>
                        <TextField fullWidth size="small" type="number" 
                          value={settings.cost_gsm_device} onChange={(e) => handleChange('cost_gsm_device', e.target.value)} />
                     </Grid>
                     <Grid size={{ xs: 8 }}><Typography variant="body2">Koszt Montażu GPS</Typography></Grid>
                     <Grid size={{ xs: 4 }}>
                        <TextField fullWidth size="small" type="number" 
                          value={settings.cost_gsm_installation} onChange={(e) => handleChange('cost_gsm_installation', e.target.value)} />
                     </Grid>
                   </Grid>
                </Grid>

                <Grid size={{ xs: 12, md: 4 }}>
                   <Typography variant="subtitle2" color="primary" gutterBottom>Akcesoria Dodatkowe</Typography>
                   <Divider sx={{ mb: 1 }} />
                   <Grid container spacing={2} alignItems="center">
                     <Grid size={{ xs: 8 }}><Typography variant="body2">Montaż Haka Holowniczego</Typography></Grid>
                     <Grid size={{ xs: 4 }}>
                        <TextField fullWidth size="small" type="number" 
                          value={settings.cost_hook_installation} onChange={(e) => handleChange('cost_hook_installation', e.target.value)} />
                     </Grid>
                     <Grid size={{ xs: 8 }}><Typography variant="body2">Demontaż Kraty</Typography></Grid>
                     <Grid size={{ xs: 4 }}>
                        <TextField fullWidth size="small" type="number" 
                          value={settings.cost_grid_dismantling} onChange={(e) => handleChange('cost_grid_dismantling', e.target.value)} />
                     </Grid>
                   </Grid>
                </Grid>

                <Grid size={{ xs: 12, md: 4 }}>
                   <Typography variant="subtitle2" color="primary" gutterBottom>Opłaty Logistyczne</Typography>
                   <Divider sx={{ mb: 1 }} />
                   <Grid container spacing={2} alignItems="center">
                     <Grid size={{ xs: 8 }}><Typography variant="body2">Koszt Rejestracji (Polska)</Typography></Grid>
                     <Grid size={{ xs: 4 }}>
                        <TextField fullWidth size="small" type="number" 
                          value={settings.cost_registration} onChange={(e) => handleChange('cost_registration', e.target.value)} />
                     </Grid>
                     <Grid size={{ xs: 8 }}><Typography variant="body2">Przygotowanie do sprzedaży (PDI)</Typography></Grid>
                     <Grid size={{ xs: 4 }}>
                        <TextField fullWidth size="small" type="number" 
                          value={settings.cost_sales_prep} onChange={(e) => handleChange('cost_sales_prep', e.target.value)} />
                     </Grid>
                   </Grid>
                </Grid>
              </Grid>
            </Paper>
          </Grid>
          
          {/* Wiersz 3: Tabela Kosztów Opon */}
          <Grid size={{ xs: 12 }}>
             <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography fontWeight="bold" color="primary">Koszty Opon (Tabela Referencyjna)</Typography>
                </AccordionSummary>
                <AccordionDetails>
                   <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
                     <Button variant="contained" size="small" onClick={handleAddTyreCost}>Dodaj Koszt Opony</Button>
                   </Box>
                   <Table size="small">
                      <TableHead>
                         <TableRow>
                            <TableCell>Klasa Opon</TableCell>
                            <TableCell>Średnica</TableCell>
                            <TableCell>Cena Zakupu</TableCell>
                            <TableCell>Cena Odkupu</TableCell>
                            <TableCell align="right">Akcje</TableCell>
                         </TableRow>
                      </TableHead>
                      <TableBody>
                         {tyreCosts.map((tc, idx) => (
                           <TableRow key={idx}>
                              <TableCell>
                                <TextField size="small" placeholder="Np. Premium" value={tc.tyre_class} onChange={(e) => handleUpdateTyreCost(idx, 'tyre_class', e.target.value)} />
                              </TableCell>
                              <TableCell>
                                <TextField size="small" type="number" placeholder="Np. 17" value={tc.diameter} onChange={(e) => handleUpdateTyreCost(idx, 'diameter', Number(e.target.value))} />
                              </TableCell>
                              <TableCell>
                                <TextField size="small" type="number" value={tc.purchase_price} onChange={(e) => handleUpdateTyreCost(idx, 'purchase_price', Number(e.target.value))} />
                              </TableCell>
                              <TableCell>
                                <TextField size="small" type="number" value={tc.buyback_price} onChange={(e) => handleUpdateTyreCost(idx, 'buyback_price', Number(e.target.value))} />
                              </TableCell>
                              <TableCell align="right">
                                 <Button size="small" color="primary" onClick={() => handleSaveTyreCost(idx)}>Zapisz</Button>
                                 <Button size="small" color="error" onClick={() => handleDeleteTyreCost(idx)}>Usuń</Button>
                              </TableCell>
                           </TableRow>
                         ))}
                      </TableBody>
                   </Table>
                </AccordionDetails>
             </Accordion>
          </Grid>

          {/* Sekcja dolna - Supabase Sync Info */}
          <Grid size={{ xs: 12 }}>
            <Paper sx={{ p: 3, bgcolor: '#f4f6f8' }} elevation={0}>
              <Typography variant="subtitle1" fontWeight="bold" color="primary" gutterBottom>
                Status Bazy Danych (Supabase)
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Formularz powiązany jest dwustronnie z tabelą `control_center` instancji w Supabase. Zapisanie ustawień ma wpływ na bieżące kalkulacje.
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* Modal - SAMAR Segmentacja (Markdown) */}
      <Dialog open={modalOpen} onClose={() => setModalOpen(false)} maxWidth="lg" fullWidth>
        <DialogTitle sx={{ fontWeight: 'bold' }}>Macierz Segmentacji SAMAR</DialogTitle>
        <DialogContent dividers>
          <Box
            sx={{
              '& table': { borderCollapse: 'collapse', width: '100%', mb: 2 },
              '& th, & td': { border: '1px solid #ddd', p: 1, fontSize: '0.875rem' },
              '& th': { backgroundColor: '#f5f5f5', fontWeight: 'bold' }
            }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {SAMAR_MARKDOWN}
            </ReactMarkdown>
          </Box>
        </DialogContent>
      </Dialog>
      </Box>
      )}

      {activeTab === 1 && <SamarRVPanel />}
    </Box>
  );
}

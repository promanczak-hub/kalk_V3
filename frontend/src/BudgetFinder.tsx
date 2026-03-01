import React, { useState } from 'react';
import {
  Box, Typography, TextField, Button, Grid, CircularProgress, Divider,
  ToggleButton, ToggleButtonGroup, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Checkbox,
  Tooltip, Collapse, IconButton, Select, MenuItem, InputLabel, FormControl, OutlinedInput,
  Chip, ListItemText, InputAdornment, Slider
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';

interface MatrixRow {
  Okres: number;
  Przebieg: number;
  RataMC: number;
  RataMC_Brutto?: number;
  KwotaWykupu?: number;
  KwotaWykupu_Brutto?: number;
}

interface BudgetVariant {
  id: string;
  dane_pojazdu: string;
  cena_netto: number;
  rata_mc: number;
  wklad_wlasny_pct: number;
  wklad_wlasny_kwota: number;
  marza_pct: number;
  wariant_nazwa: string;
  score?: number;
}

const FUEL_OPTIONS = ['Petrol', 'Diesel', 'Electric', 'Hybrid', 'MHEV', 'PHEV'];
const TRANSMISSION_OPTIONS = ['Automatic', 'Manual'];
const BODY_OPTIONS = ['SUV', 'Hatchback', 'Sedan', 'Kombi', 'Coupe', 'Liftback', 'Van', 'Pickup', 'Cabriolet', 'Minibus'];
const SAMAR_OPTIONS = ['Small', 'Lower Medium', 'Upper Medium', 'Executive', 'Luxury', 'SUV/Crossover', 'Minivan', 'Sports', 'Utility', 'Mini', 'Compact'];

const MenuProps = {
  PaperProps: {
    style: {
      maxHeight: 48 * 4.5 + 8,
      width: 250,
    },
  },
};

function MultiSelectFilter({ 
  label, options, value, onChange 
}: { 
  label: string, options: string[], value: string[], onChange: (v: string[]) => void 
}) {
  const handleChange = (event: SelectChangeEvent<typeof value>) => {
    const { target: { value: val } } = event;
    onChange(typeof val === 'string' ? val.split(',') : val);
  };

  return (
    <FormControl fullWidth size="small" sx={{ mb: 2 }}>
      <InputLabel>{label}</InputLabel>
      <Select
        multiple
        value={value}
        onChange={handleChange}
        input={<OutlinedInput label={label} />}
        renderValue={(selected) => (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {selected.map((val) => (
              <Chip key={val} label={val} size="small" />
            ))}
          </Box>
        )}
        MenuProps={MenuProps}
      >
        {options.map((name) => (
          <MenuItem key={name} value={name}>
            <Checkbox checked={value.includes(name)} />
            <ListItemText primary={name} />
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}

interface MatrixRow {
  Okres: number;
  Przebieg: number;
  RataMC: number;
  RataMC_Brutto?: number;
  KwotaWykupu?: number;
  KwotaWykupu_Brutto?: number;
}

function Row({ variant, targetRate }: { variant: BudgetVariant, targetRate: number }) {
  const [open, setOpen] = useState(false);
  const [matrixData, setMatrixData] = useState<MatrixRow[] | null>(null);
  const [loadingMatrix, setLoadingMatrix] = useState(false);
  const [matrixError, setMatrixError] = useState<string | null>(null);

  const handleExpand = async () => {
    const willOpen = !open;
    setOpen(willOpen);

    if (willOpen && matrixData === null) {
      setLoadingMatrix(true);
      setMatrixError(null);
      try {
        const response = await fetch(
          `http://127.0.0.1:8000/api/budget-finder/matrix?kalkulacja_id=${variant.id}&marza_pct=${variant.marza_pct}&wklad_wlasny_pct=${variant.wklad_wlasny_pct}`
        );
        if (!response.ok) {
          throw new Error('Błąd ładowania macierzy');
        }
        const data = await response.json();
        setMatrixData(data);
      } catch (err) {
        setMatrixError(err instanceof Error ? err.message : 'Wystąpił błąd');
      } finally {
        setLoadingMatrix(false);
      }
    }
  };

  const getHeatmapColor = (rata: number, minRata: number, maxRata: number) => {
    if (rata === 999999) return 'transparent';
    if (maxRata === minRata) return 'hsla(120, 70%, 50%, 0.3)';
    const ratio = (rata - minRata) / (maxRata - minRata);
    const hue = (1 - ratio) * 120;
    return `hsla(${hue}, 70%, 50%, 0.4)`;
  };

  let uniqueOkres: number[] = [];
  let uniquePrzebieg: number[] = [];
  let minRata = 999999;
  let maxRata = 0;

  if (matrixData) {
    uniqueOkres = Array.from(new Set(matrixData.map((m: MatrixRow) => m.Okres))).sort((a: number, b: number) => a - b);
    uniquePrzebieg = Array.from(new Set(matrixData.map((m: MatrixRow) => m.Przebieg))).sort((a: number, b: number) => a - b);
    const activeRaty = matrixData.map((m: MatrixRow) => m.RataMC);
    minRata = Math.min(...activeRaty, 999999);
    maxRata = Math.max(...activeRaty, 0);
  }

  const getMatrixValue = (okres: number, przebieg: number) => {
    return matrixData?.find((m: MatrixRow) => m.Okres === okres && m.Przebieg === przebieg);
  };

  return (
    <React.Fragment>
      <TableRow sx={{ '& > *': { borderBottom: 'unset' } }}>
        <TableCell>
          <IconButton
            aria-label="expand row"
            size="small"
            onClick={handleExpand}
          >
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell component="th" scope="row">
          <Typography variant="body2" fontWeight="bold" color="primary.main">
            {variant.wariant_nazwa}
          </Typography>
        </TableCell>
        <TableCell sx={{ minWidth: 200 }}>{variant.dane_pojazdu || 'Brak opisu pojazdu'}</TableCell>
        <TableCell align="right" sx={{ fontWeight: 'bold', color: 'success.main', minWidth: 100 }}>
          {variant.rata_mc.toFixed(2)} PLN
        </TableCell>
        <TableCell align="center" sx={{ fontWeight: 'bold', color: 'secondary.main' }}>
          {variant.score ? `${variant.score}/100` : '-'}
        </TableCell>
        <TableCell align="right">{variant.wklad_wlasny_pct.toFixed(2)}%</TableCell>
        <TableCell align="right">{variant.wklad_wlasny_kwota.toLocaleString('pl-PL', { style: 'currency', currency: 'PLN' })}</TableCell>
        <TableCell align="right">{variant.marza_pct.toFixed(2)}%</TableCell>
        <TableCell align="right" sx={{ minWidth: 120 }}>{variant.cena_netto.toLocaleString('pl-PL', { style: 'currency', currency: 'PLN' })}</TableCell>
        <TableCell align="right">
          <Button variant="outlined" size="small" onClick={() => window.location.href = `/?id=${variant.id}`}>
            Otwórz
          </Button>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={10}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom component="div" fontWeight="bold">
                Lokalna Mapa Ciepła (Rata Netto vs Parametry)
              </Typography>
              
              {loadingMatrix && (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                   <CircularProgress size={30} />
                </Box>
              )}

              {matrixError && (
                <Typography color="error.main" variant="body2" sx={{ p: 2 }}>
                  {matrixError}
                </Typography>
              )}

              {matrixData && !loadingMatrix && !matrixError && (
                <Table size="small" aria-label="matrix" sx={{ minWidth: 650 }}>
                  <TableHead>
                    <TableRow sx={{ bgcolor: 'primary.light' }}>
                      <TableCell sx={{ fontWeight: 'bold', color: 'primary.contrastText' }}>Okres / Przebieg</TableCell>
                      {uniquePrzebieg.map((p) => (
                        <TableCell key={p} align="center" sx={{ fontWeight: 'bold', color: 'primary.contrastText' }}>{p} km</TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {uniqueOkres.map((okres) => (
                      <TableRow key={okres} hover>
                        <TableCell component="th" scope="row" sx={{ fontWeight: 'bold' }}>
                          {okres} msc
                        </TableCell>
                        {uniquePrzebieg.map((przebieg) => {
                          const cellData = getMatrixValue(okres, przebieg);
                          const isUnderBudget = cellData ? cellData.RataMC <= targetRate : false;
                          const bgColor = cellData ? getHeatmapColor(cellData.RataMC, minRata, maxRata) : 'inherit';
                          return (
                            <TableCell key={przebieg} align="center" sx={{ backgroundColor: bgColor, border: isUnderBudget ? '2px solid #2e7d32' : '1px solid #e0e0e0', transition: '0.3s' }}>
                              {cellData ? (
                                  <Tooltip title={isUnderBudget ? "Poniżej budżetu docelowego!" : ""} placement="top">
                                      <Typography variant="body2" sx={{ fontWeight: isUnderBudget ? 'bold' : 'normal', color: isUnderBudget ? 'success.dark' : 'text.primary' }}>
                                          {cellData.RataMC.toFixed(2)}
                                      </Typography>
                                  </Tooltip>
                              ) : '-'}
                            </TableCell>
                          );
                        })}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </React.Fragment>
  );
}

export default function BudgetFinder() {
  const [targetRate, setTargetRate] = useState<number>(3000);
  const [tolerance, setTolerance] = useState<number>(200);
  
  // Advanced Sliders
  const [monthsRange, setMonthsRange] = useState<number[]>([24, 60]);
  const [mileageRange, setMileageRange] = useState<number[]>([10000, 60000]);
  const [marginRange, setMarginRange] = useState<number[]>([3, 10]);
  
  // Upfront
  const [upfrontType, setUpfrontType] = useState<'pct' | 'pln'>('pct');
  const [maxUpfrontValue, setMaxUpfrontValue] = useState<number>(10);
  
  // Multi-Selects
  const [fuels, setFuels] = useState<string[]>([]);
  const [transmissions, setTransmissions] = useState<string[]>([]);
  const [bodies, setBodies] = useState<string[]>([]);
  const [samarCategories, setSamarCategories] = useState<string[]>([]);

  const [results, setResults] = useState<BudgetVariant[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpfrontTypeChange = (
    _event: React.MouseEvent<HTMLElement>,
    newType: 'pct' | 'pln' | null
  ) => {
    if (newType !== null) {
      setUpfrontType(newType);
      if (newType === 'pct') {
        setMaxUpfrontValue(10);
      } else {
        setMaxUpfrontValue(20000);
      }
    }
  };

  const handleSearch = async () => {
    setLoading(true);
    setError(null);
    try {
      const url = new URL("http://127.0.0.1:8000/api/budget-finder");
      url.searchParams.append("target_rate", targetRate.toString());
      url.searchParams.append("tolerance", tolerance.toString());
      
      // Range filters
      url.searchParams.append("months_min", monthsRange[0].toString());
      url.searchParams.append("months_max", monthsRange[1].toString());
      url.searchParams.append("mileage_min", mileageRange[0].toString());
      url.searchParams.append("mileage_max", mileageRange[1].toString());
      url.searchParams.append("margin_min", marginRange[0].toString());
      url.searchParams.append("margin_max", marginRange[1].toString());
      
      url.searchParams.append("max_upfront_value", maxUpfrontValue.toString());
      url.searchParams.append("upfront_type", upfrontType);

      // Multi-Select arrays
      fuels.forEach(f => url.searchParams.append("fuels", f));
      transmissions.forEach(t => url.searchParams.append("transmissions", t));
      bodies.forEach(b => url.searchParams.append("bodies", b));
      samarCategories.forEach(s => url.searchParams.append("samar_categories", s));

      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error("Błąd podczas pobierania ofert z API");
      }
      const data = await response.json();
      setResults(data.results || []);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(String(err));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Grid container spacing={3}>
      {/* Sidebar - Filtry */}
      <Grid size={{ xs: 12, md: 3 }}>
        <Box sx={{ p: 3, border: '1px solid #e0e0e0', borderRadius: 2, backgroundColor: '#f9fafb' }}>
          <Typography variant="h6" gutterBottom fontWeight="bold" color="primary.main">
            Filtry Budżetu
          </Typography>
          <Divider sx={{ mb: 3 }} />
          
          <Typography variant="body2" fontWeight="bold" gutterBottom>Rata Docelowa Netto</Typography>
          <TextField 
            fullWidth type="number" size="small" value={targetRate} 
            onChange={(e) => setTargetRate(Number(e.target.value))} sx={{ mb: 2 }}
            InputProps={{ endAdornment: <InputAdornment position="end">PLN</InputAdornment> }}
          />
          
          <Typography variant="body2" fontWeight="bold" gutterBottom>Tolerancja Rate (+/-)</Typography>
          <TextField 
            fullWidth type="number" size="small" value={tolerance} 
            onChange={(e) => setTolerance(Number(e.target.value))} sx={{ mb: 3 }}
            InputProps={{ endAdornment: <InputAdornment position="end">PLN</InputAdornment> }}
          />

          <Typography variant="body2" fontWeight="bold" gutterBottom>Wpłata Własna (Max)</Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 3 }}>
            <ToggleButtonGroup value={upfrontType} exclusive onChange={handleUpfrontTypeChange} size="small" fullWidth>
              <ToggleButton value="pct">Procentowa [%]</ToggleButton>
              <ToggleButton value="pln">Kwotowa [PLN]</ToggleButton>
            </ToggleButtonGroup>
            <TextField 
              fullWidth type="number" size="small" value={maxUpfrontValue} 
              onChange={(e) => setMaxUpfrontValue(Number(e.target.value))}
              InputProps={{ endAdornment: <InputAdornment position="end">{upfrontType === 'pct' ? '%' : 'PLN'}</InputAdornment> }}
            />
          </Box>
          
          <Typography variant="h6" gutterBottom fontWeight="bold" color="primary.main" sx={{ mt: 2 }}>
            Parametry Skrajne
          </Typography>
          <Divider sx={{ mb: 3 }} />

          <Typography variant="body2" fontWeight="bold" gutterBottom>Okres Finansowania (Msc)</Typography>
          <Box sx={{ px: 1, mb: 2 }}>
            <Slider
              value={monthsRange}
              onChange={(_e: Event, newValue: number | number[]) => setMonthsRange(newValue as number[])}
              valueLabelDisplay="auto"
              min={24}
              max={60}
              step={6}
              marks={[ {value: 24, label: '24'}, {value: 36, label: '36'}, {value: 48, label: '48'}, {value: 60, label: '60'} ]}
            />
          </Box>

          <Typography variant="body2" fontWeight="bold" gutterBottom>Przebieg Roczny (km)</Typography>
          <Box sx={{ px: 1, mb: 2 }}>
            <Slider
              value={mileageRange}
              onChange={(_e: Event, newValue: number | number[]) => setMileageRange(newValue as number[])}
              valueLabelDisplay="auto"
              min={10000}
              max={60000}
              step={10000}
              marks={[ {value: 10000, label: '10k'}, {value: 60000, label: '60k'} ]}
            />
          </Box>

          <Typography variant="body2" fontWeight="bold" gutterBottom>Elastyczność Marży LTR (%)</Typography>
          <Box sx={{ px: 1, mb: 3 }}>
            <Slider
              value={marginRange}
              onChange={(_e: Event, newValue: number | number[]) => setMarginRange(newValue as number[])}
              valueLabelDisplay="auto"
              min={0}
              max={20}
              step={0.5}
            />
          </Box>
          
          <Typography variant="h6" gutterBottom fontWeight="bold" color="primary.main" sx={{ mt: 2 }}>
            Filtry Samochodu
          </Typography>
          <Divider sx={{ mb: 3 }} />

          <MultiSelectFilter label="Rodzaj Paliwa" options={FUEL_OPTIONS} value={fuels} onChange={setFuels} />
          <MultiSelectFilter label="Skrzynia Biegów" options={TRANSMISSION_OPTIONS} value={transmissions} onChange={setTransmissions} />
          <MultiSelectFilter label="Typ Nadwozia" options={BODY_OPTIONS} value={bodies} onChange={setBodies} />
          <MultiSelectFilter label="Klasa SAMAR" options={SAMAR_OPTIONS} value={samarCategories} onChange={setSamarCategories} />

          <Button 
            variant="contained" color="primary" fullWidth size="large"
            onClick={handleSearch} disabled={loading} sx={{ py: 1.5, mt: 2, fontWeight: 'bold' }}
          >
            {loading ? <CircularProgress size={24} color="inherit" /> : "Skanuj Oferty Budżetowe"}
          </Button>
        </Box>
      </Grid>

      {/* Główne okno - Wyniki w Tabeli */}
      <Grid size={{ xs: 12, md: 9 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h5" color="primary.dark" fontWeight="bold">Rejestr Ofert Budżetowych</Typography>
            <Typography variant="subtitle1" color="textSecondary">{results.length} Zgodnych Ofert</Typography>
        </Box>
        <Divider sx={{ mb: 3 }} />
        
        {error && <Typography color="error" sx={{ mb: 2, fontWeight: 'bold' }}>{error}</Typography>}
        
        {!loading && results.length === 0 && !error && (
            <Box sx={{ p: 4, textAlign: 'center', bgcolor: 'background.paper', borderRadius: 2, border: '1px dashed #ccc' }}>
              <Typography variant="body1" color="textSecondary">
                Zdefiniuj kryteria po lewej stronie i uruchom wyszukiwanie. Zintegrowana Heatmapa uwidoczni najbardziej zyskowne profile kontraktu.
              </Typography>
            </Box>
        )}

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {!loading && results.length > 0 && (
          <TableContainer component={Paper} elevation={2} sx={{ borderRadius: 2, overflow: 'hidden' }}>
            <Table aria-label="collapsible table" size="medium">
              <TableHead sx={{ bgcolor: 'grey.100' }}>
                <TableRow>
                  <TableCell />
                  <TableCell sx={{ fontWeight: 'bold' }}>Wariant Finansowania</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Model Pojazdu</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>Rata Netto</TableCell>
                  <TableCell align="center" sx={{ fontWeight: 'bold' }}>Zgodność (Heatmap)</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>Wpłata (%)</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>Wpłata (PLN)</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>Marża LTR</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>Cena Katalogowa</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>Akcja</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {results.map((variant) => (
                  <Row key={`${variant.id}-${variant.wariant_nazwa}`} variant={variant} targetRate={targetRate} />
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Grid>
    </Grid>
  );
}

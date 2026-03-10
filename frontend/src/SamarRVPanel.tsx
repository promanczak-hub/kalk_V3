import { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Grid,
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
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import axios from "axios";

// Interfaces mapping to standard RV structure
interface SamarClass {
  id: number;
  nazwa: string;
  stawka_serwis_km: number;
  koszt_przegladu_podstawowego: number;
}

interface BasePercentage {
  id: number;
  samar_class_id: number;
  rodzaj_paliwa: number;
  korekta_procent: number;
}

interface BrandCorrection {
  id: number;
  marka_id: number;
  brand_name?: string;
  model_name?: string;
  notes?: string;
  samar_class_id: number;
  rodzaj_paliwa: number;
  korekta_procent: number;
}

interface AgeDepreciation {
  id: number;
  rok: number;
  samar_class_id: number;
  rodzaj_paliwa: number;
  korekta_procent: number;
}

interface MileageCorrection {
  id: number;
  samar_class_id: number;
  korekta_procent_ponizej_190: number;
  korekta_procent_powyzej_190: number;
}

interface InsuranceRate {
  id: number;
  samar_class_id: number;
  KolejnyRok: number;
  StawkaBazowaAC: number;
  SkladkaOC: number;
  samar_klasa_wr?: {
    nazwa: string;
  };
}

interface InsuranceCoefficient {
  id: number;
  samar_class_id: number;
  WspSredniPrzebieg: number;
  WspWartoscSzkody: number;
  samar_klasa_wr?: {
    nazwa: string;
  };
}

const SamarClassRow = ({
  row,
  onSave,
}: {
  row: SamarClass;
  onSave: (r: SamarClass) => void;
}) => {
  const [editing, setEditing] = useState(false);
  const [stawka, setStawka] = useState(row.stawka_serwis_km);
  const [koszt, setKoszt] = useState(row.koszt_przegladu_podstawowego);

  return (
    <TableRow>
      <TableCell>{row.id}</TableCell>
      <TableCell>{row.nazwa}</TableCell>
      <TableCell>
        {editing ? (
          <input
            type="number"
            step="0.01"
            value={stawka}
            onChange={(e) => setStawka(parseFloat(e.target.value))}
            style={{ width: 80 }}
          />
        ) : (
          `${row.stawka_serwis_km?.toFixed(2) || "0.00"}`
        )}
      </TableCell>
      <TableCell>
        {editing ? (
          <input
            type="number"
            step="10"
            value={koszt}
            onChange={(e) => setKoszt(parseFloat(e.target.value))}
            style={{ width: 100 }}
          />
        ) : (
          `${row.koszt_przegladu_podstawowego?.toFixed(2) || "0.00"}`
        )}
      </TableCell>
      <TableCell align="right">
        {editing ? (
          <button
            onClick={() => {
              onSave({
                ...row,
                stawka_serwis_km: stawka,
                koszt_przegladu_podstawowego: koszt,
              });
              setEditing(false);
            }}
          >
            Zapisz
          </button>
        ) : (
          <button onClick={() => setEditing(true)}>
            Edytuj Konfig. Serwisu
          </button>
        )}
      </TableCell>
    </TableRow>
  );
};

export default function SamarRVPanel() {
  const [classes, setClasses] = useState<SamarClass[]>([]);
  const [basePct, setBasePct] = useState<BasePercentage[]>([]);
  const [brandCorr, setBrandCorr] = useState<BrandCorrection[]>([]);
  const [ageDepr, setAgeDepr] = useState<AgeDepreciation[]>([]);
  const [mileageCorr, setMileageCorr] = useState<MileageCorrection[]>([]);
  
  // Insurance State
  const [insuranceRates, setInsuranceRates] = useState<InsuranceRate[]>([]);
  const [insuranceCoefficients, setInsuranceCoefficients] = useState<InsuranceCoefficient[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [cls, bas, brd, age, mil, insRates, insCoeffs] = await Promise.all([
        axios.get<SamarClass[]>(`${import.meta.env.VITE_API_URL || ""}/api/samar-rv/classes`),
        axios.get<BasePercentage[]>(
          `${import.meta.env.VITE_API_URL || ""}/api/samar-rv/base-percentages`,
        ),
        axios.get<BrandCorrection[]>(
          `${import.meta.env.VITE_API_URL || ""}/api/samar-rv/brand-corrections`,
        ),
        axios.get<AgeDepreciation[]>(
          `${import.meta.env.VITE_API_URL || ""}/api/samar-rv/depreciation`,
        ),
        axios.get<MileageCorrection[]>(
          `${import.meta.env.VITE_API_URL || ""}/api/samar-rv/mileage`,
        ),
        axios.get<InsuranceRate[]>(
          `${import.meta.env.VITE_API_URL || ""}/api/samar-rv/insurance-rates`,
        ),
        axios.get<InsuranceCoefficient[]>(
          `${import.meta.env.VITE_API_URL || ""}/api/samar-rv/insurance-coefficients`,
        ),
      ]);

      setClasses(cls.data);
      setBasePct(bas.data);
      setBrandCorr(brd.data);
      setAgeDepr(age.data);
      setMileageCorr(mil.data);
      setInsuranceRates(insRates.data);
      setInsuranceCoefficients(insCoeffs.data);

      setError(null);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : "Nieznany błąd podczas pobierania danych SAMAR RV.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getClassName = (id: number) => {
    return classes.find((c) => c.id === id)?.nazwa || `ID: ${id}`;
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 5 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" color="primary" fontWeight="bold" gutterBottom>
        Panel Administracyjny SAMAR RV (Tylko odczyt)
      </Typography>
      <Alert severity="info" sx={{ mb: 2 }}>
        Poniższe tabele pochodzą docelowo z V1 MSSQL. Kalkulator odpytuje o nie
        przez API. Aby zmienić wartości, należy użyć narzędzi bazodanowych z
        uwagi na wymaganą historyzację LTR.
      </Alert>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12 }}>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography fontWeight="bold">Tabela 1: Klasy SAMAR</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>ID Klasy</TableCell>
                    <TableCell>Nazwa Segmentu / Typ</TableCell>
                    <TableCell>Stawka Serwis / KM (PLN)</TableCell>
                    <TableCell>Koszt Podst. Przeglądu / Rok (PLN)</TableCell>
                    <TableCell align="right">Akcje</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {classes.map((c) => (
                    <SamarClassRow
                      key={c.id}
                      row={c}
                      onSave={async (updatedClass) => {
                        try {
                          const res = await axios.post(
                            `${import.meta.env.VITE_API_URL || ""}/api/samar-rv/classes`,
                            updatedClass,
                          );
                          setClasses((prev) =>
                            prev.map((p) =>
                              p.id === res.data.id ? res.data : p,
                            ),
                          );
                          alert("Zapisano pomyślnie.");
                        } catch (err) {
                          alert("Błąd zapisu.");
                          console.error(err);
                        }
                      }}
                    />
                  ))}
                </TableBody>
              </Table>
            </AccordionDetails>
          </Accordion>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography fontWeight="bold">
                Tabela 2: Wartości Bazowe (% RV)
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Klasa SAMAR</TableCell>
                    <TableCell>Rodzaj Paliwa (1=Ben, 2=Die, 3=EV)</TableCell>
                    <TableCell>Korekta %</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {basePct.map((b) => (
                    <TableRow key={b.id}>
                      <TableCell>{b.id}</TableCell>
                      <TableCell>{getClassName(b.samar_class_id)}</TableCell>
                      <TableCell>{b.rodzaj_paliwa}</TableCell>
                      <TableCell>
                        {(b.korekta_procent * 100).toFixed(2)} %
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </AccordionDetails>
          </Accordion>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography fontWeight="bold">
                Tabela 3: Korekta za Wiek (Lata)
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Rok eksploatacji</TableCell>
                    <TableCell>Klasa SAMAR</TableCell>
                    <TableCell>Rodzaj Paliwa</TableCell>
                    <TableCell>Korekta % (Deprecjacja)</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {ageDepr.map((a) => (
                    <TableRow key={a.id}>
                      <TableCell>{a.id}</TableCell>
                      <TableCell>{a.rok}</TableCell>
                      <TableCell>{getClassName(a.samar_class_id)}</TableCell>
                      <TableCell>{a.rodzaj_paliwa}</TableCell>
                      <TableCell>
                        {(a.korekta_procent * 100).toFixed(2)} %
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </AccordionDetails>
          </Accordion>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography fontWeight="bold">
                Tabela 4: Korekta za Przebieg
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Klasa SAMAR</TableCell>
                    <TableCell>Spadek RV / 1000km (do 190 tys.)</TableCell>
                    <TableCell>Spadek RV / 1000km (powyżej 190 tys.)</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {mileageCorr.map((m) => (
                    <TableRow key={m.id}>
                      <TableCell>{m.id}</TableCell>
                      <TableCell>{getClassName(m.samar_class_id)}</TableCell>
                      <TableCell>
                        {(m.korekta_procent_ponizej_190 * 100).toFixed(4)} %
                      </TableCell>
                      <TableCell>
                        {(m.korekta_procent_powyzej_190 * 100).toFixed(4)} %
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </AccordionDetails>
          </Accordion>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography fontWeight="bold">
                Tabela 5: Korekta (Narzut) na Markę
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Marka (Nazwa)</TableCell>
                    <TableCell>Model (Opcjonalnie)</TableCell>
                    <TableCell>Klasa SAMAR</TableCell>
                    <TableCell>Rodzaj Paliwa</TableCell>
                    <TableCell>Rating / Narzut %</TableCell>
                    <TableCell>ID Eurotax</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {brandCorr.map((b) => (
                    <TableRow key={b.id}>
                      <TableCell>{b.id}</TableCell>
                      <TableCell>{b.brand_name || "-"}</TableCell>
                      <TableCell>{b.model_name || "-"}</TableCell>
                      <TableCell>{getClassName(b.samar_class_id)}</TableCell>
                      <TableCell>{b.rodzaj_paliwa}</TableCell>
                      <TableCell>
                        {(b.korekta_procent * 100).toFixed(2)} %
                      </TableCell>
                      <TableCell>{b.marka_id || "-"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </AccordionDetails>
          </Accordion>
        </Grid>
        
        {/* V1 Insurance Integrations */}
        <Grid size={{ xs: 12 }}>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography fontWeight="bold" color="secondary">
                [V1 Import] Tabela: Stawki Ubezpieczeniowe
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Klasa Samochodu</TableCell>
                    <TableCell>Rok Użytkowania</TableCell>
                    <TableCell>Stawka Bazowa AC (%)</TableCell>
                    <TableCell>Składka OC (PLN)</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {insuranceRates.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell>{r.id}</TableCell>
                      <TableCell>{r.samar_klasa_wr?.nazwa || r.samar_class_id}</TableCell>
                      <TableCell>{r.KolejnyRok}</TableCell>
                      <TableCell>
                        {(r.StawkaBazowaAC * 100).toFixed(2)} %
                      </TableCell>
                      <TableCell>{r.SkladkaOC.toFixed(2)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </AccordionDetails>
          </Accordion>
        </Grid>
        
        <Grid size={{ xs: 12 }}>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography fontWeight="bold" color="secondary">
                [V1 Import] Tabela: Współczynniki Szkodowe
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Klasa Samochodu</TableCell>
                    <TableCell>Współczynnik Przebiegu</TableCell>
                    <TableCell>Współczynnik Szkody</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {insuranceCoefficients.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell>{c.id}</TableCell>
                      <TableCell>{c.samar_klasa_wr?.nazwa || c.samar_class_id}</TableCell>
                      <TableCell>{c.WspSredniPrzebieg.toFixed(4)}</TableCell>
                      <TableCell>{c.WspWartoscSzkody.toFixed(4)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </AccordionDetails>
          </Accordion>
        </Grid>
      </Grid>
    </Box>
  );

}

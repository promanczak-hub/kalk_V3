import React, { useState } from "react";
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import axios from "axios";
import type { V1DataOption } from "./types";

// Types for settings
interface ControlCenterSettings {
  default_wibor: number;
  default_ltr_margin: number;
  vat_rate?: number;
}

// Mock data based on json
const INITIAL_DATA: V1DataOption = {
  Numer: "0467/02/26",
  KalkulacjaId: 170315,
  OpcjeFabryczne: [
    {
      Id: 1,
      Nazwa: "Szary Graphite metalizowany",
      CenaNetto: 2926.83,
      Cena: 3600.0,
      isNierabatowany: false,
      WR: false,
    },
    {
      Id: 2,
      Nazwa: "PakietInfotainment(RN0)",
      CenaNetto: 4146.34,
      Cena: 5100.0,
      isNierabatowany: false,
      WR: false,
    },
  ],
  OpcjeSerwisowe: [],
  StawkaVat: 0.23,
  Marza: 0.13,
  RodzajCzynszu: "Kwotowo",
  CzynszKwota: 0.0,
  CzynszProcent: 0.0,
  CzynszInicjalny: 0.0,
  OkresUzytkowania: 36,
  Przebieg: 120000,
  Rocznik: "bieżący",
  Marka: "SKODA",
  Model: {
    Id: 12161,
    Typ: "Model",
    DN: "SKODA Superb 1,5 PHEV Hybrydowy 2x4 AT",
  },
  WersjaNadwozia: "5 drzwiowy",
  KategoriaSamar: "GRUPA PODSTAWOWA",
  MocSilnika: "264",
  WersjaWyposazenia: "Drive",
  RodzajPaliwa: "Hybrydowy",
  HomologacjaSelected: "Osobowy",
  KlasaWR: "D",
  ZOponami: true,
  RozmiarOpon: { Szerokosc: "215", Profil: "60", Litera: "R", Srednica: "16" },
  KlasaOpon: "BLIZNIACZE",
  LiczbaKompletowOponSelected: "Automatycznie",
  OdkupOpon: false,
  InneKosztySerwisowania: 0.0,
  PakietSerwisowy: 0.0,
  PakietSerwisowyNazwa: null,
  KorektaRV: 0.0,
  KalkulacjaWolumenowa: null,
  WiborProcent: 0.0482,
  MarzaFinansowaProcent: 0.022,
  ProcentAmortyzacji: 0.0091,
  Opis: null,
  Prywatna: false,
  CenaCennikowaNetto: 164430.89,
  CenaCennikowa: 202250.0,
  Metalik: true,
  TypRabatu: "Procentowo",
  RabatProcent: 0.24,
  RabatKwotaNetto: 41160.98,
  RabatKwota: 50628.0,
  SamochodZastepczy: true,
  ExpressPlaciUbezpieczenie: true,
  CzyUwzgledniaSerwisowanie: true,
  CzyGPS: true,
  DoubezpieczenieKradziezy: null,
  NaukaJazdy: null,
  KosztUbezpieczeniaKorekta: 0.0,
  KosztPrzygotowaniaDosprzedazyKorekta: 0.0,
  KosztOponKorekta: 0.0,
  GlownyMatrixParameters: {
    CzynszFinansowyRazem: { Wartosc: 64660.0 },
    CzynszTechnicznyRazem: { Wartosc: 21650.0 },
    KosztRazem: { Wartosc: 86310.0 },
    LacznieUbezpieczenie: { Wartosc: 13952.0 },
    KosztTechnicznySerwis: { Wartosc: 0.0 },
    KosztTechnicznyOpony: { Wartosc: 3891.0 },
    KosztTechnicznySamochodZastepczy: { Wartosc: 2145.0 },
    KosztyDodatkowe: { Wartosc: 1662.0 },
  },
};

// Small helper for Field Label mimicking V1 dense right-aligned labels
const FieldLabel = ({
  label,
  mock = false,
}: {
  label: string;
  mock?: boolean;
}) => (
  <Typography
    align="right"
    variant="body2"
    sx={{ pr: 2, fontSize: "0.8rem", color: "#333" }}
  >
    {label}{" "}
    {mock && <span style={{ color: "red", fontWeight: "bold" }}>!</span>}
  </Typography>
);

export default function CalculatorPanel() {
  const [data, setData] = useState<V1DataOption>(INITIAL_DATA);
  const [expanded, setExpanded] = useState<string | false>("panel1");
  const [settings, setSettings] = useState<ControlCenterSettings | null>(null);

  const [isParserOpen, setIsParserOpen] = useState(false);
  const [parserText, setParserText] = useState("");
  const [isParsing, setIsParsing] = useState(false);

  React.useEffect(() => {
    fetchSettings();
    const params = new URLSearchParams(window.location.search);
    const id = params.get("id");
    if (id) {
      loadKalkulacja(id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadKalkulacja = async (id: string) => {
    try {
      const resp = await axios.get(
        `http://127.0.0.1:8000/api/kalkulacje/${id}`,
      );
      if (resp.data && resp.data.stan_json) {
        applyParsedOffer(resp.data.stan_json, resp.data.numer_kalkulacji);
      }
    } catch (e) {
      console.error("Failed to load kalkulacja", e);
    }
  };

  const fetchSettings = async () => {
    try {
      const resp = await axios.get<ControlCenterSettings>(
        "http://127.0.0.1:8000/api/control-center",
      );
      setSettings(resp.data);
      // Opcjonalnie nadpisz domyślny formularz
      if (resp.data) {
        setData((prev) => ({
          ...prev,
          StawkaVat: (resp.data.vat_rate || 23) / 100,
          WiborProcent: (resp.data.default_wibor || 4.82) / 100, 
          MarzaFinansowaProcent: (resp.data.default_ltr_margin || 1.35) / 100,
        }));
      }
    } catch (e) {
      console.error("Failed to fetch settings", e);
    }
  };

  const handleChange =
    (panel: string) => (_event: React.SyntheticEvent, isExpanded: boolean) => {
      setExpanded(isExpanded ? panel : false);
    };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleUpdate = (field: keyof V1DataOption, value: any) => {
    setData((prev) => ({ ...prev, [field]: value }));
  };

  const handleUpdateNetto = (netto: number) => {
    setData((prev) => {
      const vat = prev.StawkaVat || 0.23;
      const brutto = netto * (1 + vat);
      let rabatProcent = prev.RabatProcent;
      let rabatKwota = prev.RabatKwota;
      let rabatKwotaNetto = prev.RabatKwotaNetto;

      if (prev.TypRabatu === "Procentowo") {
        rabatKwota = brutto * rabatProcent;
        rabatKwotaNetto = netto * rabatProcent;
      } else {
        rabatProcent = brutto > 0 ? rabatKwota / brutto : 0;
      }
      return {
        ...prev,
        CenaCennikowaNetto: netto,
        CenaCennikowa: brutto,
        RabatProcent: rabatProcent,
        RabatKwota: rabatKwota,
        RabatKwotaNetto: rabatKwotaNetto,
      };
    });
  };

  const handleUpdateBrutto = (brutto: number) => {
    setData((prev) => {
      const vat = prev.StawkaVat || 0.23;
      const netto = brutto / (1 + vat);
      let rabatProcent = prev.RabatProcent;
      let rabatKwota = prev.RabatKwota;
      let rabatKwotaNetto = prev.RabatKwotaNetto;

      if (prev.TypRabatu === "Procentowo") {
        rabatKwota = brutto * rabatProcent;
        rabatKwotaNetto = netto * rabatProcent;
      } else {
        rabatProcent = brutto > 0 ? rabatKwota / brutto : 0;
      }
      return {
        ...prev,
        CenaCennikowaNetto: netto,
        CenaCennikowa: brutto,
        RabatProcent: rabatProcent,
        RabatKwota: rabatKwota,
        RabatKwotaNetto: rabatKwotaNetto,
      };
    });
  };

  const handleUpdateRabat = (typ: string, value: number) => {
    setData((prev) => {
      const vat = prev.StawkaVat || 0.23;
      const brutto = prev.CenaCennikowa;
      const netto = prev.CenaCennikowaNetto;
      let rabatProcent = prev.RabatProcent;
      let rabatKwota = prev.RabatKwota;
      let rabatKwotaNetto = prev.RabatKwotaNetto;

      if (typ === "Procentowo") {
        rabatProcent = value / 100;
        rabatKwota = brutto * rabatProcent;
        rabatKwotaNetto = netto * rabatProcent;
      } else {
        rabatKwota = value;
        rabatKwotaNetto = value / (1 + vat);
        rabatProcent = brutto > 0 ? rabatKwota / brutto : 0;
      }
      return {
        ...prev,
        TypRabatu: typ,
        RabatProcent: rabatProcent,
        RabatKwota: rabatKwota,
        RabatKwotaNetto: rabatKwotaNetto,
      };
    });
  };


  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const applyParsedOffer = (parsedRaw: any, numer_kalkulacji?: string) => {
    let parsed = parsedRaw;
    
    // Obsługa danych bezpośrednio z VertexExtractor (SynthesisResponse)
    if (parsedRaw && parsedRaw.card_summary && !parsedRaw.factory_options) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const parsePrice = (val: any) => {
        if (typeof val === 'number') return val;
        if (!val) return 0;
        let s = String(val).replace(/\s/g, '').replace(/[^\d,.-]/g, '');
        if (s.includes('.') && s.includes(',')) s = s.replace(/\./g, '');
        s = s.replace(',', '.');
        return parseFloat(s) || 0;
      };

      const cs = parsedRaw.card_summary;
      
      const factoryOptions = (cs.paid_options || [])
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        .filter((o: any) => o.category === "Fabryczna")
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        .map((o: any) => ({ name: o.name, price_net: parsePrice(o.price) }));
        
      const dealerOptions = (cs.paid_options || [])
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        .filter((o: any) => o.category !== "Fabryczna")
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        .map((o: any) => ({ name: o.name, price_net: parsePrice(o.price) }));

      let discountAmt = 0;
      try {
        const pages = parsedRaw.digital_twin?.pages || [];
        for (const p of pages) {
           for (const s of (p.sections || [])) {
               if (s.data && Array.isArray(s.data)) {
                   for (const item of s.data) {
                       if (item.category === "Rabat" || item.item === "Rabat") {
                          discountAmt = parsePrice(item.price_net || item.price || 0);
                       }
                   }
               }
           }
        }
      } catch (e) { console.error(e); }

      parsed = {
        brand: parsedRaw.brand || "",
        model: parsedRaw.model || "",
        trim: parsedRaw.trim || "",
        base_price_net: parsePrice(cs.base_price),
        factory_options: factoryOptions,
        dealer_options: dealerOptions,
        tire_size: cs.wheels || "",
        discount_amount_net: Math.abs(discountAmt),
        discount_pct: 0,
        fuel_type: "Diesel", // Domyslnie dla LCV jako fallback
        body_style: cs.body_style || "",
        samar_category: "KLASYFIKACJA...",
        power_hp: parsedRaw.digital_twin?.technical_data?.power_hp || "",
      };
    }

    setData((prev) => {
      const vat = prev.StawkaVat || 0.23;

      // Opcje fabryczne
      let nextFactoryId =
        prev.OpcjeFabryczne.length > 0
          ? Math.max(...prev.OpcjeFabryczne.map((o) => o.Id)) + 1
          : 1;
      const newFactoryOptions = (parsed.factory_options || []).map(
        (fo: { name: string; price_net: number }) => ({
          Id: nextFactoryId++,
          Nazwa: fo.name,
          CenaNetto: fo.price_net,
          Cena: fo.price_net * (1 + vat),
          isNierabatowany: false,
          WR: false,
        }),
      );

      // Opcje serwisowe
      let nextServiceId =
        prev.OpcjeSerwisowe.length > 0
          ? Math.max(...prev.OpcjeSerwisowe.map((o) => o.Id)) + 1
          : 1;
      const newServiceOptions = (parsed.dealer_options || []).map(
        (so: { name: string; price_net: number }) => ({
          Id: nextServiceId++,
          Nazwa: so.name,
          CenaNetto: so.price_net,
          Cena: so.price_net * (1 + vat),
          isNierabatowany: false,
          WR: false,
        }),
      );

      const bruttoBase = (parsed.base_price_net || 0) * (1 + vat);

      // Opony parsing (AAA/BB RCC)
      let opony = prev.RozmiarOpon;
      if (parsed.tire_size) {
        const regex = /^(\d{3})\/(\d{2})\s*(R)(\d{2})/i;
        const match = parsed.tire_size.match(regex);
        if (match) {
          opony = {
            Szerokosc: match[1],
            Profil: match[2],
            Litera: match[3],
            Srednica: match[4],
          };
        }
      }

      let rabatKwotaNetto = parsed.discount_amount_net || 0;
      let rabatKwota = rabatKwotaNetto * (1 + vat);
      let rabatProcent = bruttoBase > 0 ? rabatKwota / bruttoBase : 0;

      if (parsed.discount_pct && parsed.discount_pct > 0) {
        rabatProcent = parsed.discount_pct;
        rabatKwotaNetto = parsed.base_price_net * rabatProcent;
        rabatKwota = bruttoBase * rabatProcent;
      }

      return {
        ...prev,
        Numer: numer_kalkulacji || prev.Numer,
        Marka: parsed.brand || prev.Marka,
        Model: {
          ...prev.Model,
          DN: parsed.model + (parsed.trim ? ` ${parsed.trim}` : ""),
        },
        WersjaNadwozia: parsed.body_style || prev.WersjaNadwozia,
        KategoriaSamar: parsed.samar_category || prev.KategoriaSamar,
        MocSilnika: parsed.power_hp ? String(parsed.power_hp) : prev.MocSilnika,
        RodzajPaliwa: parsed.fuel_type || prev.RodzajPaliwa,
        CenaCennikowaNetto: parsed.base_price_net || 0,
        CenaCennikowa: bruttoBase || 0,
        OpcjeFabryczne: newFactoryOptions, // Zawsze zastępuj przy parsowaniu oferty
        OpcjeSerwisowe: newServiceOptions,
        TypRabatu: "Kwotowo",
        RabatKwotaNetto: rabatKwotaNetto,
        RabatKwota: rabatKwota,
        RabatProcent: rabatProcent,
        RozmiarOpon: opony,
      };
    });

    const classificationBrand = parsedRaw.brand || parsed.brand || "";
    const classificationModel = parsedRaw.model || parsed.model || "";
    const classificationBody = parsedRaw.card_summary?.body_style || parsed.body_style || parsed.trim || "";

    if (classificationBrand || classificationModel) {
      axios.post("http://127.0.0.1:8000/api/parse-offer/samar-category", {
        brand: classificationBrand,
        model: classificationModel,
        body_style: classificationBody
      }).then((resp) => {
         if (resp.data?.samar_category) {
           setData((prev) => ({ ...prev, KategoriaSamar: resp.data.samar_category }));
         }
      }).catch((err) => {
         console.error("SAMAR LLM error", err);
         setData((prev) => ({ ...prev, KategoriaSamar: "INNE" }));
      });
    }
  };

  const handleParseOffer = async () => {
    if (!parserText.trim()) return;
    setIsParsing(true);
    try {
      const resp = await axios.post("http://127.0.0.1:8000/api/parse-offer", {
        raw_text: parserText,
      });
      applyParsedOffer(resp.data);

      setIsParserOpen(false);
      setParserText("");
    } catch (err) {
      console.error("Parse offer error", err);
      alert("Błąd podczas przetwarzania oferty. Sprawdź logi serwera.");
    } finally {
      setIsParsing(false);
    }
  };

  const handleChangeTypRabatu = (typ: "Procentowo" | "Kwotowo") => {
    setData((prev) => {
      return { ...prev, TypRabatu: typ };
    });
  };

  return (
    <Box sx={{ pb: 5, backgroundColor: "#fcfcfc", minHeight: "100vh" }}>
      {/* Top Banner (Wizytówka equivalent) */}
      <Box
        sx={{ p: 2, borderBottom: "1px solid #ddd", mb: 2, bgcolor: "#fff" }}
      >
        <Typography variant="h5" fontWeight="bold" sx={{ mb: 2 }}>
          Kalkulacja {data.Numer}
        </Typography>

        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <Button variant="contained" size="small" sx={{ bgcolor: "#1e3a8a" }}>
            Zleć akceptację DZA{" "}
            <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
          </Button>
          <Button variant="contained" size="small" sx={{ bgcolor: "#1e3a8a" }}>
            Akceptacja DZA{" "}
            <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
          </Button>
          <Button variant="contained" size="small" sx={{ bgcolor: "#1e3a8a" }}>
            Pokaż Matrix{" "}
            <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
          </Button>
          <Button variant="contained" size="small" sx={{ bgcolor: "#1e3a8a" }}>
            Odakceptuj <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
          </Button>
          <Button variant="contained" size="small" sx={{ bgcolor: "#1e3a8a" }}>
            Podejmij ofertę dealera{" "}
            <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
          </Button>
          <Button
            variant="contained"
            size="small"
            color="secondary"
            onClick={() => setIsParserOpen(true)}
          >
            Zrozum Ofertę (LLM){" "}
            <span style={{ color: "yellow", marginLeft: 4 }}>✨</span>
          </Button>
          <Button variant="contained" size="small" color="primary">
            Zapisz i przelicz
          </Button>
        </Box>
        <Box sx={{ display: "flex", gap: 1, mt: 1, flexWrap: "wrap" }}>
          <Button variant="contained" size="small" sx={{ bgcolor: "#1e3a8a" }}>
            Zleć akceptację handlową{" "}
            <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
          </Button>
          <Button variant="contained" size="small" sx={{ bgcolor: "#1e3a8a" }}>
            Akceptacja Handlowa{" "}
            <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
          </Button>
          <Button variant="contained" size="small" sx={{ bgcolor: "#1e3a8a" }}>
            Zleć akceptację DT{" "}
            <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
          </Button>
          <Button variant="contained" size="small" sx={{ bgcolor: "#1e3a8a" }}>
            Akceptacja DT{" "}
            <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
          </Button>
          <Button variant="contained" size="small" sx={{ bgcolor: "#1e3a8a" }}>
            Zleć akceptację WR{" "}
            <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
          </Button>
          <Button variant="contained" size="small" sx={{ bgcolor: "#1e3a8a" }}>
            Akceptacja WR{" "}
            <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
          </Button>
        </Box>
      </Box>

      <Box
        sx={{
          px: 2,
          display: "flex",
          flexDirection: "column",
          gap: 2,
          maxWidth: "1400px",
          margin: "0 auto",
        }}
      >
        {/* Wizytówka */}
        <Accordion
          expanded={expanded === "panel0"}
          onChange={handleChange("panel0")}
          sx={{ border: "1px solid #1e3a8a", "&:before": { display: "none" } }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon sx={{ color: "white" }} />}
            sx={{
              bgcolor: "#1e3a8a",
              color: "white",
              minHeight: "36px",
              "& .MuiAccordionSummary-content": { my: 1 },
            }}
          >
            <Typography variant="body2" fontWeight="bold">
              Wizytówka
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ p: 2 }}>
            <Typography variant="body2" color="textSecondary">
              Dane wizytówki...
            </Typography>
          </AccordionDetails>
        </Accordion>

        {/* Załączniki */}
        <Accordion
          expanded={expanded === "panel_zalaczniki"}
          onChange={handleChange("panel_zalaczniki")}
          sx={{ border: "1px solid #1e3a8a", "&:before": { display: "none" } }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon sx={{ color: "white" }} />}
            sx={{
              bgcolor: "#1e3a8a",
              color: "white",
              minHeight: "36px",
              "& .MuiAccordionSummary-content": { my: 1 },
            }}
          >
            <Typography variant="body2" fontWeight="bold">
              Załączniki
            </Typography>
          </AccordionSummary>
          <AccordionDetails
            sx={{
              p: 2,
              display: "flex",
              gap: 2,
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <Button
              variant="contained"
              size="small"
              sx={{ bgcolor: "#1e3a8a" }}
            >
              Wybierz plik{" "}
              <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
            </Button>
            <Box>
              <Button
                variant="contained"
                size="small"
                sx={{ bgcolor: "#1e3a8a", mr: 1 }}
              >
                Otwórz galerię{" "}
                <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
              </Button>
              <Button
                variant="contained"
                size="small"
                sx={{ bgcolor: "#1e3a8a" }}
              >
                Pobierz wszystkie{" "}
                <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
              </Button>
            </Box>
          </AccordionDetails>
        </Accordion>

        {/* Dane kontraktu */}
        <Accordion
          defaultExpanded
          sx={{ border: "1px solid #1e3a8a", "&:before": { display: "none" } }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon sx={{ color: "white" }} />}
            sx={{
              bgcolor: "#1e3a8a",
              color: "white",
              minHeight: "36px",
              "& .MuiAccordionSummary-content": { my: 1 },
            }}
          >
            <Typography variant="body2" fontWeight="bold">
              Dane kontraktu
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ p: 3 }}>
            <Grid container spacing={4}>
              {/* Kolumna Lewa */}
              <Grid size={{ xs: 12, md: 6 }}>
                <Grid container spacing={1} alignItems="center">
                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Produkt" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Typography
                      variant="body2"
                      color="primary"
                      sx={{ cursor: "pointer", fontSize: "0.8rem" }}
                    >
                      LTR
                    </Typography>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Klient" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Typography
                      variant="body2"
                      color="primary"
                      sx={{ cursor: "pointer", fontSize: "0.8rem" }}
                    >
                      CBRE Sp. z o.o. +48509300163
                    </Typography>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Handlowiec Express" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Typography
                      variant="body2"
                      color="primary"
                      sx={{ cursor: "pointer", fontSize: "0.8rem" }}
                    >
                      Paweł Romańczak
                    </Typography>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Oferta dealera" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Typography
                      variant="body2"
                      color="primary"
                      sx={{ cursor: "pointer", fontSize: "0.8rem" }}
                    >
                      brak
                    </Typography>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Rodzaj oferty" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Select
                      size="small"
                      fullWidth
                      defaultValue="Oferta wolumenowa"
                      sx={{ height: 28, fontSize: "0.8rem" }}
                    >
                      <MenuItem value="Oferta wolumenowa">
                        Oferta wolumenowa
                      </MenuItem>
                    </Select>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Marża %" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      size="small"
                      fullWidth
                      value={data.Marza * 100}
                      onChange={(e) =>
                        handleUpdate("Marza", Number(e.target.value) / 100)
                      }
                      sx={{
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                        },
                      }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Dostosuj stawkę" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Checkbox size="small" sx={{ p: 0.5 }} />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Okres użytkowania" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      size="small"
                      fullWidth
                      type="number"
                      value={data.OkresUzytkowania}
                      onChange={(e) =>
                        handleUpdate("OkresUzytkowania", Number(e.target.value))
                      }
                      sx={{
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                        },
                      }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Przebieg końcowy" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      size="small"
                      fullWidth
                      type="number"
                      value={data.Przebieg}
                      onChange={(e) =>
                        handleUpdate("Przebieg", Number(e.target.value))
                      }
                      sx={{
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                        },
                      }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Rocznik" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Select
                      size="small"
                      fullWidth
                      value={data.Rocznik}
                      onChange={(e) => handleUpdate("Rocznik", e.target.value)}
                      sx={{ height: 28, fontSize: "0.8rem" }}
                    >
                      <MenuItem value="bieżący">bieżący</MenuItem>
                      <MenuItem value="poprzedni">poprzedni</MenuItem>
                    </Select>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Model" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Typography
                      variant="body2"
                      color="primary"
                      sx={{ cursor: "pointer", fontSize: "0.8rem" }}
                    >
                      {data.Model.DN}
                    </Typography>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Wersja nadwozia" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Select
                      size="small"
                      fullWidth
                      value={data.WersjaNadwozia}
                      onChange={(e) =>
                        handleUpdate("WersjaNadwozia", e.target.value)
                      }
                      sx={{ height: 28, fontSize: "0.8rem" }}
                    >
                      <MenuItem value="5 drzwiowy">5 drzwiowy</MenuItem>
                      <MenuItem value="Kombi">Kombi</MenuItem>
                    </Select>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Wersja wyposażenia" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Select
                      size="small"
                      fullWidth
                      value={data.WersjaWyposazenia}
                      onChange={(e) =>
                        handleUpdate("WersjaWyposazenia", e.target.value)
                      }
                      sx={{ height: 28, fontSize: "0.8rem" }}
                    >
                      <MenuItem value="Drive">Drive</MenuItem>
                      <MenuItem value="Ultra Bright">Ultra Bright</MenuItem>
                    </Select>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Rodzaj kosztów" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Select
                      size="small"
                      fullWidth
                      defaultValue="ASO"
                      sx={{ height: 28, fontSize: "0.8rem" }}
                    >
                      <MenuItem value="ASO">ASO</MenuItem>
                    </Select>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Moc silnika" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      size="small"
                      fullWidth
                      value={data.MocSilnika}
                      onChange={(e) =>
                        handleUpdate("MocSilnika", e.target.value)
                      }
                      sx={{
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                        },
                      }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Rodzaj paliwa" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      size="small"
                      fullWidth
                      disabled
                      value={data.RodzajPaliwa}
                      sx={{
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                          bgcolor: "#f5f5f5",
                        },
                      }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Homologacja" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Select
                      size="small"
                      fullWidth
                      value={data.HomologacjaSelected}
                      onChange={(e) =>
                        handleUpdate("HomologacjaSelected", e.target.value)
                      }
                      sx={{ height: 28, fontSize: "0.8rem" }}
                    >
                      <MenuItem value="Osobowy">Osobowy</MenuItem>
                      <MenuItem value="Ciężarowy">Ciężarowy</MenuItem>
                    </Select>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Hak holowniczy" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Checkbox size="small" sx={{ p: 0.5 }} />
                  </Grid>

                  {/* KATEGORIA SAMAR - Artefakt parsowania */}
                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Kategoria SAMAR" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      size="small"
                      fullWidth
                      disabled
                      value={data.KategoriaSamar || "-"}
                      sx={{
                        "& .MuiInputBase-input.Mui-disabled": {
                          WebkitTextFillColor: "#0277bd",
                        },
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                          bgcolor: "#e1f5fe",
                          fontWeight: "bold",
                        },
                      }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Klasa wynajmu" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Select
                      size="small"
                      fullWidth
                      defaultValue="F"
                      sx={{ height: 28, fontSize: "0.8rem" }}
                    >
                      <MenuItem value="F">F</MenuItem>
                    </Select>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Klasa WR" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Typography
                      variant="body2"
                      sx={{ fontSize: "0.8rem", pt: 0.5 }}
                    >
                      {data.KlasaWR}
                    </Typography>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Rodzaj czynszu" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Select
                      size="small"
                      fullWidth
                      value={data.RodzajCzynszu}
                      onChange={(e) =>
                        handleUpdate("RodzajCzynszu", e.target.value)
                      }
                      sx={{ height: 28, fontSize: "0.8rem" }}
                    >
                      <MenuItem value="Kwotowo">Kwotowo</MenuItem>
                      <MenuItem value="Procentowo">Procentowo</MenuItem>
                    </Select>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Czynsz kwota" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      size="small"
                      fullWidth
                      type="number"
                      value={data.CzynszKwota}
                      onChange={(e) =>
                        handleUpdate("CzynszKwota", Number(e.target.value))
                      }
                      sx={{
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                        },
                      }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Czynsz inicjalny do kalkulatora" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      size="small"
                      fullWidth
                      type="number"
                      value={data.CzynszInicjalny}
                      onChange={(e) =>
                        handleUpdate("CzynszInicjalny", Number(e.target.value))
                      }
                      sx={{
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                          bgcolor: "#f0f0f0",
                        },
                      }}
                    />
                  </Grid>
                </Grid>
              </Grid>

              {/* Kolumna Prawa */}
              <Grid size={{ xs: 12, md: 6 }}>
                <Grid container spacing={1} alignItems="center">
                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Czy z oponami" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Checkbox
                      checked={data.ZOponami}
                      onChange={(e) =>
                        handleUpdate("ZOponami", e.target.checked)
                      }
                      size="small"
                      sx={{ p: 0.5 }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Rozmiar opon" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Select
                      size="small"
                      fullWidth
                      defaultValue="18"
                      sx={{ height: 28, fontSize: "0.8rem" }}
                    >
                      <MenuItem value="16">16</MenuItem>
                      <MenuItem value="18">18</MenuItem>
                    </Select>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Klasa opon" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Select
                      size="small"
                      fullWidth
                      value={data.KlasaOpon}
                      onChange={(e) =>
                        handleUpdate("KlasaOpon", e.target.value)
                      }
                      sx={{ height: 28, fontSize: "0.8rem" }}
                    >
                      <MenuItem value="PREMIUM">PREMIUM</MenuItem>
                      <MenuItem value="BLIZNIACZE">BLIZNIACZE</MenuItem>
                    </Select>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Liczba kompletów opon" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Select
                      size="small"
                      fullWidth
                      value={data.LiczbaKompletowOponSelected}
                      onChange={(e) =>
                        handleUpdate(
                          "LiczbaKompletowOponSelected",
                          e.target.value,
                        )
                      }
                      sx={{ height: 28, fontSize: "0.8rem" }}
                    >
                      <MenuItem value="Automatycznie">Automatycznie</MenuItem>
                      <MenuItem value="1">1</MenuItem>
                      <MenuItem value="2">2</MenuItem>
                    </Select>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Inne koszty serwisowania" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      size="small"
                      fullWidth
                      value={data.InneKosztySerwisowania}
                      type="number"
                      sx={{
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                        },
                      }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Pakiet serwisowy kwota" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      size="small"
                      fullWidth
                      value={data.PakietSerwisowy}
                      type="number"
                      sx={{
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                        },
                      }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Pakiet serwisowy nazwa" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      size="small"
                      fullWidth
                      value={data.PakietSerwisowyNazwa || ""}
                      sx={{
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                        },
                      }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Korekta WR" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      size="small"
                      fullWidth
                      value={data.KorektaRV}
                      type="number"
                      sx={{
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                        },
                      }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Kalkulacja wolumenowa" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Checkbox
                      checked={!!data.KalkulacjaWolumenowa}
                      size="small"
                      sx={{ p: 0.5 }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Wibor" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    {settings ? (
                      <TextField
                        size="small"
                        fullWidth
                        value={settings.default_wibor}
                        type="number"
                        sx={{
                          "& .MuiInputBase-root": {
                            height: 28,
                            fontSize: "0.8rem",
                            bgcolor: "#f5f5f5",
                          },
                        }}
                        disabled
                      />
                    ) : (
                      <CircularProgress size={16} />
                    )}
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Marża finansowa" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    {settings ? (
                      <TextField
                        size="small"
                        fullWidth
                        value={settings.default_ltr_margin}
                        type="number"
                        sx={{
                          "& .MuiInputBase-root": {
                            height: 28,
                            fontSize: "0.8rem",
                            bgcolor: "#f5f5f5",
                          },
                        }}
                        disabled
                      />
                    ) : (
                      <CircularProgress size={16} />
                    )}
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Procent amortyzacji" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      size="small"
                      fullWidth
                      value={data.ProcentAmortyzacji * 100}
                      type="number"
                      sx={{
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                          bgcolor: "#f5f5f5",
                        },
                      }}
                      disabled
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Opis" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      size="small"
                      fullWidth
                      value={data.Opis || ""}
                      sx={{
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                        },
                      }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Blokada edycji" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Checkbox size="small" sx={{ p: 0.5 }} />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Prywatna" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Checkbox
                      checked={data.Prywatna}
                      onChange={(e) =>
                        handleUpdate("Prywatna", e.target.checked)
                      }
                      size="small"
                      sx={{ p: 0.5 }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="BB" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Checkbox size="small" sx={{ p: 0.5 }} />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Projekt CRM" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      size="small"
                      fullWidth
                      sx={{
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                        },
                      }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Uwagi do oferty dealera" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      multiline
                      rows={4}
                      fullWidth
                      defaultValue="brak oferty"
                      sx={{ "& .MuiInputBase-root": { fontSize: "0.8rem" } }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Uwagi do kalkulacji" mock />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <TextField
                      multiline
                      rows={4}
                      fullWidth
                      sx={{ "& .MuiInputBase-root": { fontSize: "0.8rem" } }}
                    />
                  </Grid>
                </Grid>
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Kalkulacja samochodu */}
        <Accordion
          defaultExpanded
          sx={{ border: "1px solid #1e3a8a", "&:before": { display: "none" } }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon sx={{ color: "white" }} />}
            sx={{
              bgcolor: "#1e3a8a",
              color: "white",
              minHeight: "36px",
              "& .MuiAccordionSummary-content": { my: 1 },
            }}
          >
            <Typography variant="body2" fontWeight="bold">
              Kalkulacja samochodu
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ p: 3 }}>
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid size={{ xs: 12, md: 6 }}>
                <Grid container spacing={1} alignItems="center">
                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Cena cennikowa netto" />
                  </Grid>
                  <Grid
                    size={{ xs: 7 }}
                    sx={{ display: "flex", gap: 1, alignItems: "center" }}
                  >
                    <TextField
                      size="small"
                      type="number"
                      value={data.CenaCennikowaNetto.toFixed(2)}
                      onChange={(e) =>
                        handleUpdateNetto(Number(e.target.value))
                      }
                      sx={{
                        flex: 1,
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                        },
                      }}
                    />
                    <Typography variant="body2" sx={{ fontSize: "0.8rem" }}>
                      brutto
                    </Typography>
                    <TextField
                      size="small"
                      type="number"
                      value={data.CenaCennikowa.toFixed(2)}
                      onChange={(e) =>
                        handleUpdateBrutto(Number(e.target.value))
                      }
                      sx={{
                        flex: 1,
                        "& .MuiInputBase-root": {
                          height: 28,
                          fontSize: "0.8rem",
                        },
                      }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Metalik" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Checkbox
                      checked={data.Metalik}
                      onChange={(e) =>
                        handleUpdate("Metalik", e.target.checked)
                      }
                      size="small"
                      sx={{ p: 0.5 }}
                    />
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel label="Typ rabatu" />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    <Select
                      size="small"
                      fullWidth
                      value={data.TypRabatu}
                      onChange={(e) =>
                        handleChangeTypRabatu(
                          e.target.value as "Procentowo" | "Kwotowo",
                        )
                      }
                      sx={{ height: 28, fontSize: "0.8rem", maxWidth: 150 }}
                    >
                      <MenuItem value="Procentowo">Procentowo</MenuItem>
                      <MenuItem value="Kwotowo">Kwotowo</MenuItem>
                    </Select>
                  </Grid>

                  <Grid size={{ xs: 5 }}>
                    <FieldLabel
                      label={
                        data.TypRabatu === "Procentowo"
                          ? "Rabat %"
                          : "Rabat (Kwota Brutto)"
                      }
                    />
                  </Grid>
                  <Grid size={{ xs: 7 }}>
                    {data.TypRabatu === "Procentowo" ? (
                      <TextField
                        size="small"
                        type="number"
                        value={(data.RabatProcent * 100).toFixed(2)}
                        onChange={(e) =>
                          handleUpdateRabat(
                            "Procentowo",
                            Number(e.target.value),
                          )
                        }
                        sx={{
                          "& .MuiInputBase-root": {
                            height: 28,
                            fontSize: "0.8rem",
                          },
                          maxWidth: 100,
                        }}
                      />
                    ) : (
                      <TextField
                        size="small"
                        type="number"
                        value={data.RabatKwota.toFixed(2)}
                        onChange={(e) =>
                          handleUpdateRabat("Kwotowo", Number(e.target.value))
                        }
                        sx={{
                          "& .MuiInputBase-root": {
                            height: 28,
                            fontSize: "0.8rem",
                          },
                          maxWidth: 100,
                        }}
                      />
                    )}
                  </Grid>
                </Grid>
              </Grid>
            </Grid>

            {/* Opcje Fabryczne / Serwisowe Tabele */}
            <Grid container spacing={2}>
              {/* Opcje fabryczne */}
              <Grid size={{ xs: 12, md: 6 }}>
                <TableContainer
                  component={Paper}
                  elevation={0}
                  sx={{ border: "1px solid #ccc" }}
                >
                  <Box
                    sx={{
                      bgcolor: "#4caf50",
                      color: "white",
                      px: 2,
                      py: 1,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <Typography variant="body2" fontWeight="bold">
                      Opcje fabryczne
                    </Typography>
                    <Button
                      size="small"
                      variant="contained"
                      sx={{
                        bgcolor: "#1e3a8a",
                        height: 24,
                        fontSize: "0.7rem",
                      }}
                    >
                      Dodaj{" "}
                      <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
                    </Button>
                  </Box>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontSize: "0.7rem" }}>Nazwa</TableCell>
                        <TableCell sx={{ fontSize: "0.7rem", width: 90 }}>
                          Cena netto
                        </TableCell>
                        <TableCell sx={{ fontSize: "0.7rem", width: 90 }}>
                          Cena brutto
                        </TableCell>
                        <TableCell sx={{ fontSize: "0.7rem", width: 50 }}>
                          Bez rabatu
                        </TableCell>
                        <TableCell
                          sx={{ fontSize: "0.7rem", width: 60 }}
                        ></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.OpcjeFabryczne.map((opt, i) => (
                        <TableRow key={i}>
                          <TableCell sx={{ p: 0.5 }}>
                            <TextField
                              size="small"
                              fullWidth
                              value={opt.Nazwa}
                              sx={{
                                "& .MuiInputBase-root": {
                                  height: 24,
                                  fontSize: "0.75rem",
                                },
                              }}
                            />
                          </TableCell>
                          <TableCell sx={{ p: 0.5 }}>
                            <TextField
                              size="small"
                              type="number"
                              fullWidth
                              value={opt.CenaNetto}
                              sx={{
                                "& .MuiInputBase-root": {
                                  height: 24,
                                  fontSize: "0.75rem",
                                },
                              }}
                            />
                          </TableCell>
                          <TableCell sx={{ p: 0.5 }}>
                            <TextField
                              size="small"
                              type="number"
                              fullWidth
                              value={opt.Cena}
                              sx={{
                                "& .MuiInputBase-root": {
                                  height: 24,
                                  fontSize: "0.75rem",
                                },
                              }}
                            />
                          </TableCell>
                          <TableCell sx={{ p: 0.5, textAlign: "center" }}>
                            <Checkbox
                              checked={opt.isNierabatowany}
                              size="small"
                              sx={{ p: 0 }}
                            />
                          </TableCell>
                          <TableCell sx={{ p: 0.5 }}>
                            <Button
                              size="small"
                              variant="contained"
                              sx={{
                                bgcolor: "#1e3a8a",
                                height: 24,
                                minWidth: 40,
                                px: 1,
                                fontSize: "0.7rem",
                              }}
                            >
                              Usuń
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                      <TableRow sx={{ bgcolor: "#f9f9f9" }}>
                        <TableCell
                          colSpan={5}
                          sx={{ p: 1, fontSize: "0.8rem", fontWeight: "bold" }}
                        >
                          Suma brutto:{" "}
                          {data.OpcjeFabryczne.reduce(
                            (sum, opt) => sum + opt.Cena,
                            0,
                          )}
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              </Grid>

              {/* Opcje serwisowe */}
              <Grid size={{ xs: 12, md: 6 }}>
                <TableContainer
                  component={Paper}
                  elevation={0}
                  sx={{ border: "1px solid #ccc" }}
                >
                  <Box
                    sx={{
                      bgcolor: "#4caf50",
                      color: "white",
                      px: 2,
                      py: 1,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <Typography variant="body2" fontWeight="bold">
                      Opcje serwisowe
                    </Typography>
                    <Button
                      size="small"
                      variant="contained"
                      sx={{
                        bgcolor: "#1e3a8a",
                        height: 24,
                        fontSize: "0.7rem",
                      }}
                    >
                      Dodaj{" "}
                      <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
                    </Button>
                  </Box>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontSize: "0.7rem" }}>Nazwa</TableCell>
                        <TableCell sx={{ fontSize: "0.7rem", width: 90 }}>
                          Cena netto
                        </TableCell>
                        <TableCell sx={{ fontSize: "0.7rem", width: 90 }}>
                          Cena brutto
                        </TableCell>
                        <TableCell sx={{ fontSize: "0.7rem", width: 50 }}>
                          Dolicz do WR
                        </TableCell>
                        <TableCell
                          sx={{ fontSize: "0.7rem", width: 60 }}
                        ></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.OpcjeSerwisowe.length === 0 && (
                        <TableRow>
                          <TableCell
                            colSpan={5}
                            sx={{
                              p: 2,
                              textAlign: "center",
                              color: "#999",
                              fontSize: "0.8rem",
                            }}
                          >
                            Brak opcji
                          </TableCell>
                        </TableRow>
                      )}
                      {data.OpcjeSerwisowe.map((opt, i) => (
                        <TableRow key={i}>
                          <TableCell sx={{ p: 0.5 }}>
                            <TextField
                              size="small"
                              fullWidth
                              value={opt.Nazwa}
                              sx={{
                                "& .MuiInputBase-root": {
                                  height: 24,
                                  fontSize: "0.75rem",
                                },
                              }}
                            />
                          </TableCell>
                          <TableCell sx={{ p: 0.5 }}>
                            <TextField
                              size="small"
                              type="number"
                              fullWidth
                              value={opt.CenaNetto}
                              sx={{
                                "& .MuiInputBase-root": {
                                  height: 24,
                                  fontSize: "0.75rem",
                                },
                              }}
                            />
                          </TableCell>
                          <TableCell sx={{ p: 0.5 }}>
                            <TextField
                              size="small"
                              type="number"
                              fullWidth
                              value={opt.Cena}
                              sx={{
                                "& .MuiInputBase-root": {
                                  height: 24,
                                  fontSize: "0.75rem",
                                },
                              }}
                            />
                          </TableCell>
                          <TableCell sx={{ p: 0.5, textAlign: "center" }}>
                            <Checkbox
                              checked={opt.WR}
                              size="small"
                              sx={{ p: 0 }}
                            />
                          </TableCell>
                          <TableCell sx={{ p: 0.5 }}>
                            <Button
                              size="small"
                              variant="contained"
                              sx={{
                                bgcolor: "#1e3a8a",
                                height: 24,
                                minWidth: 40,
                                px: 1,
                                fontSize: "0.7rem",
                              }}
                            >
                              Usuń
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Opcje dodatkowe */}
        <Accordion
          defaultExpanded
          sx={{ border: "1px solid #1e3a8a", "&:before": { display: "none" } }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon sx={{ color: "white" }} />}
            sx={{
              bgcolor: "#1e3a8a",
              color: "white",
              minHeight: "36px",
              "& .MuiAccordionSummary-content": { my: 1 },
            }}
          >
            <Typography variant="body2" fontWeight="bold">
              Opcje dodatkowe
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ p: 3 }}>
            <Grid container spacing={4}>
              <Grid size={{ xs: 12, md: 4 }}>
                <Typography
                  variant="body2"
                  align="center"
                  sx={{ mb: 2, fontSize: "0.8rem" }}
                >
                  Dodatkowe:
                </Typography>
                <Grid container spacing={0} alignItems="center">
                  <Grid size={{ xs: 9 }}>
                    <FieldLabel label="Czy liczony samochód zastępczy" />
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Checkbox
                      checked={data.SamochodZastepczy}
                      onChange={(e) =>
                        handleUpdate("SamochodZastepczy", e.target.checked)
                      }
                      size="small"
                    />
                  </Grid>

                  <Grid size={{ xs: 9 }}>
                    <FieldLabel label="Czy Express płaci ubezpieczenie" />
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Checkbox
                      checked={data.ExpressPlaciUbezpieczenie}
                      onChange={(e) =>
                        handleUpdate(
                          "ExpressPlaciUbezpieczenie",
                          e.target.checked,
                        )
                      }
                      size="small"
                    />
                  </Grid>

                  <Grid size={{ xs: 9 }}>
                    <FieldLabel label="Czy uwzględnia serwisowanie" />
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Checkbox
                      checked={data.CzyUwzgledniaSerwisowanie}
                      onChange={(e) =>
                        handleUpdate(
                          "CzyUwzgledniaSerwisowanie",
                          e.target.checked,
                        )
                      }
                      size="small"
                    />
                  </Grid>

                  <Grid size={{ xs: 9 }}>
                    <FieldLabel label="GPS" />
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Checkbox
                      checked={data.CzyGPS}
                      onChange={(e) => handleUpdate("CzyGPS", e.target.checked)}
                      size="small"
                    />
                  </Grid>

                  <Grid size={{ xs: 9 }}>
                    <FieldLabel label="Doubezpieczenie kradzieży" />
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Checkbox
                      checked={!!data.DoubezpieczenieKradziezy}
                      onChange={(e) =>
                        handleUpdate(
                          "DoubezpieczenieKradziezy",
                          e.target.checked,
                        )
                      }
                      size="small"
                    />
                  </Grid>

                  <Grid size={{ xs: 9 }}>
                    <FieldLabel label="Nauka jazdy" />
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Checkbox
                      checked={!!data.NaukaJazdy}
                      onChange={(e) =>
                        handleUpdate("NaukaJazdy", e.target.checked)
                      }
                      size="small"
                    />
                  </Grid>
                </Grid>
              </Grid>

              <Grid size={{ xs: 12, md: 4 }}>
                <Typography
                  variant="body2"
                  align="center"
                  sx={{ mb: 2, fontSize: "0.8rem" }}
                >
                  Ubezpieczenie dodatkowe:{" "}
                  <span style={{ color: "red", fontWeight: "bold" }}>!</span>
                </Typography>
                <Grid container spacing={0} alignItems="center">
                  <Grid size={{ xs: 9 }}>
                    <FieldLabel label="Zielona karta" mock />
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Checkbox size="small" disabled />
                  </Grid>

                  <Grid size={{ xs: 9 }}>
                    <FieldLabel label="NNW" mock />
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Checkbox size="small" disabled />
                  </Grid>

                  <Grid size={{ xs: 9 }}>
                    <FieldLabel label="ASS" mock />
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Checkbox size="small" disabled />
                  </Grid>
                </Grid>
              </Grid>

              <Grid size={{ xs: 12, md: 4 }}>
                <Typography
                  variant="body2"
                  align="center"
                  sx={{ mb: 2, fontSize: "0.8rem" }}
                >
                  Korekta:
                </Typography>
                <Grid container spacing={0} alignItems="center">
                  <Grid size={{ xs: 9 }}>
                    <FieldLabel label="Koszt ubezpieczenia" />
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Checkbox
                      checked={data.KosztUbezpieczeniaKorekta > 0}
                      onChange={(e) =>
                        handleUpdate(
                          "KosztUbezpieczeniaKorekta",
                          e.target.checked ? 1 : 0,
                        )
                      }
                      size="small"
                    />
                  </Grid>

                  <Grid size={{ xs: 9 }}>
                    <FieldLabel label="Koszt przygotowania do sprzedaży" />
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Checkbox
                      checked={data.KosztPrzygotowaniaDosprzedazyKorekta > 0}
                      onChange={(e) =>
                        handleUpdate(
                          "KosztPrzygotowaniaDosprzedazyKorekta",
                          e.target.checked ? 1 : 0,
                        )
                      }
                      size="small"
                    />
                  </Grid>

                  <Grid size={{ xs: 9 }}>
                    <FieldLabel label="Koszt opon" />
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Checkbox
                      checked={data.KosztOponKorekta > 0}
                      onChange={(e) =>
                        handleUpdate(
                          "KosztOponKorekta",
                          e.target.checked ? 1 : 0,
                        )
                      }
                      size="small"
                    />
                  </Grid>
                </Grid>
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Podsumowanie kalkulacji */}
        <Accordion
          expanded={expanded === "panel_podsumowanie"}
          onChange={handleChange("panel_podsumowanie")}
          sx={{ border: "1px solid #1e3a8a", "&:before": { display: "none" } }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon sx={{ color: "white" }} />}
            sx={{
              bgcolor: "#1e3a8a",
              color: "white",
              minHeight: "36px",
              "& .MuiAccordionSummary-content": { my: 1 },
            }}
          >
            <Typography variant="body2" fontWeight="bold">
              Podsumowanie kalkulacji{" "}
              <span style={{ color: "yellow", marginLeft: 4 }}>!</span>
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ p: 2 }}>
            <Typography variant="body2" color="textSecondary">
              Podsumowanie...
            </Typography>
          </AccordionDetails>
        </Accordion>

        {/* Wyniki kalkulacji - szczegóły */}
        <Accordion
          defaultExpanded
          sx={{
            border: "1px solid #1e3a8a",
            "&:before": { display: "none" },
            mb: 4,
          }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon sx={{ color: "white" }} />}
            sx={{
              bgcolor: "#1e3a8a",
              color: "white",
              minHeight: "36px",
              "& .MuiAccordionSummary-content": { my: 1 },
            }}
          >
            <Typography variant="body2" fontWeight="bold">
              Wynik kalkulacji - szczegóły
            </Typography>
          </AccordionSummary>
          <AccordionDetails
            sx={{ p: 4, display: "flex", justifyContent: "center" }}
          >
            <Box sx={{ width: "100%", maxWidth: "600px" }}>
              <Box
                sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}
              >
                <Typography
                  variant="body2"
                  fontWeight="bold"
                  sx={{ fontSize: "0.8rem" }}
                >
                  Numer kalkulacji:
                </Typography>
                <Typography
                  variant="body2"
                  fontWeight="bold"
                  sx={{ fontSize: "0.8rem" }}
                >
                  {data.Numer}
                </Typography>
              </Box>

              <Box
                sx={{ display: "flex", justifyContent: "space-between", mb: 3 }}
              >
                <Typography
                  variant="body2"
                  color="textSecondary"
                  sx={{ fontSize: "0.8rem" }}
                >
                  Numer kalkulacji źródłowej:{" "}
                  <span style={{ color: "red", fontWeight: "bold" }}>!</span>
                </Typography>
                <Typography
                  variant="body2"
                  color="textSecondary"
                  sx={{ fontSize: "0.8rem" }}
                >
                  ----/--/--
                </Typography>
              </Box>

              <Grid container spacing={2} sx={{ mb: 1 }}>
                <Grid size={{ xs: 6 }}></Grid>
                <Grid size={{ xs: 3 }}>
                  <Typography
                    variant="body2"
                    align="center"
                    sx={{ fontSize: "0.8rem", color: "#666" }}
                  >
                    Wartość
                    <br />
                    netto
                  </Typography>
                </Grid>
                <Grid size={{ xs: 3 }}>
                  <Typography
                    variant="body2"
                    align="center"
                    sx={{ fontSize: "0.8rem", color: "#666" }}
                  >
                    Wartość
                    <br />
                    brutto
                  </Typography>
                </Grid>
              </Grid>

              {/* Tabela Wyników Mapowana z Jsona */}
              <Box
                sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}
              >
                <Grid size={{ xs: 6 }}>
                  <Typography
                    align="right"
                    variant="body2"
                    sx={{ pr: 2, fontSize: "0.8rem" }}
                  >
                    Czynsz inicjalny kwotowo:
                  </Typography>
                </Grid>
                <Grid size={{ xs: 3 }}>
                  <Typography
                    align="center"
                    variant="body2"
                    sx={{ fontSize: "0.8rem" }}
                  >
                    0,00
                  </Typography>
                </Grid>
                <Grid size={{ xs: 3 }}>
                  <Typography
                    align="center"
                    variant="body2"
                    sx={{ fontSize: "0.8rem" }}
                  >
                    0,00
                  </Typography>
                </Grid>
              </Box>

              <Box
                sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}
              >
                <Grid size={{ xs: 6 }}>
                  <Typography
                    align="right"
                    variant="body2"
                    sx={{ pr: 2, fontSize: "0.8rem" }}
                  >
                    Marża % na kontrakcie:
                  </Typography>
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <Typography
                    align="center"
                    variant="body2"
                    sx={{ fontSize: "0.8rem" }}
                  >
                    {(data.Marza * 100).toFixed(2)}%
                  </Typography>
                </Grid>
              </Box>

              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  mb: 1,
                  mt: 2,
                }}
              >
                <Grid size={{ xs: 6 }}>
                  <Typography
                    align="right"
                    variant="body2"
                    sx={{ pr: 2, fontSize: "0.8rem" }}
                  >
                    Stawka łączna:
                  </Typography>
                </Grid>
                <Grid size={{ xs: 3 }}>
                  <Typography
                    align="center"
                    variant="body2"
                    sx={{ fontSize: "0.8rem" }}
                  >
                    {(
                      (data.GlownyMatrixParameters?.CzynszFinansowyRazem
                        ?.Wartosc || 0) /
                        data.OkresUzytkowania +
                      (data.GlownyMatrixParameters?.CzynszTechnicznyRazem
                        ?.Wartosc || 0) /
                        data.OkresUzytkowania
                    ).toFixed(2)}
                  </Typography>
                </Grid>
                <Grid size={{ xs: 3 }}>
                  <Typography
                    align="center"
                    variant="body2"
                    sx={{ fontSize: "0.8rem" }}
                  >
                    {(
                      ((data.GlownyMatrixParameters?.CzynszFinansowyRazem
                        ?.Wartosc || 0) /
                        data.OkresUzytkowania +
                        (data.GlownyMatrixParameters?.CzynszTechnicznyRazem
                          ?.Wartosc || 0) /
                          data.OkresUzytkowania) *
                      1.23
                    ).toFixed(2)}
                  </Typography>
                </Grid>
              </Box>

              <Box
                sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}
              >
                <Grid size={{ xs: 6 }}>
                  <Typography
                    align="right"
                    variant="body2"
                    sx={{ pr: 2, fontSize: "0.8rem" }}
                  >
                    Czynsz finansowy:
                  </Typography>
                </Grid>
                <Grid size={{ xs: 3 }}>
                  <Typography
                    align="center"
                    variant="body2"
                    sx={{ fontSize: "0.8rem" }}
                  >
                    {(
                      (data.GlownyMatrixParameters?.CzynszFinansowyRazem
                        ?.Wartosc || 0) / data.OkresUzytkowania
                    ).toFixed(2)}
                  </Typography>
                </Grid>
                <Grid size={{ xs: 3 }}>
                  <Typography
                    align="center"
                    variant="body2"
                    sx={{ fontSize: "0.8rem" }}
                  >
                    {(
                      ((data.GlownyMatrixParameters?.CzynszFinansowyRazem
                        ?.Wartosc || 0) /
                        data.OkresUzytkowania) *
                      1.23
                    ).toFixed(2)}
                  </Typography>
                </Grid>
              </Box>

              <Box
                sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}
              >
                <Grid size={{ xs: 6 }}>
                  <Typography
                    align="right"
                    variant="body2"
                    sx={{ pr: 2, fontSize: "0.8rem" }}
                  >
                    Czynsz techniczny:
                  </Typography>
                </Grid>
                <Grid size={{ xs: 3 }}>
                  <Typography
                    align="center"
                    variant="body2"
                    sx={{ fontSize: "0.8rem" }}
                  >
                    {(
                      (data.GlownyMatrixParameters?.CzynszTechnicznyRazem
                        ?.Wartosc || 0) / data.OkresUzytkowania
                    ).toFixed(2)}
                  </Typography>
                </Grid>
                <Grid size={{ xs: 3 }}>
                  <Typography
                    align="center"
                    variant="body2"
                    sx={{ fontSize: "0.8rem" }}
                  >
                    {(
                      ((data.GlownyMatrixParameters?.CzynszTechnicznyRazem
                        ?.Wartosc || 0) /
                        data.OkresUzytkowania) *
                      1.23
                    ).toFixed(2)}
                  </Typography>
                </Grid>
              </Box>

              <Box sx={{ pl: 4 }}>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    mb: 1,
                  }}
                >
                  <Grid size={{ xs: 6 }}>
                    <Typography
                      align="right"
                      variant="body2"
                      sx={{ pr: 2, fontSize: "0.8rem" }}
                    >
                      Ubezpieczenie:
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Typography
                      align="center"
                      variant="body2"
                      sx={{ fontSize: "0.8rem" }}
                    >
                      {(
                        (data.GlownyMatrixParameters?.LacznieUbezpieczenie
                          ?.Wartosc || 0) / data.OkresUzytkowania
                      ).toFixed(2)}
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Typography
                      align="center"
                      variant="body2"
                      sx={{ fontSize: "0.8rem" }}
                    >
                      {(
                        ((data.GlownyMatrixParameters?.LacznieUbezpieczenie
                          ?.Wartosc || 0) /
                          data.OkresUzytkowania) *
                        1.23
                      ).toFixed(2)}
                    </Typography>
                  </Grid>
                </Box>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    mb: 1,
                  }}
                >
                  <Grid size={{ xs: 6 }}>
                    <Typography
                      align="right"
                      variant="body2"
                      sx={{ pr: 2, fontSize: "0.8rem" }}
                    >
                      Serwis:
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Typography
                      align="center"
                      variant="body2"
                      sx={{ fontSize: "0.8rem" }}
                    >
                      {(
                        (data.GlownyMatrixParameters?.KosztTechnicznySerwis
                          ?.Wartosc || 0) / data.OkresUzytkowania
                      ).toFixed(2)}
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Typography
                      align="center"
                      variant="body2"
                      sx={{ fontSize: "0.8rem" }}
                    >
                      {(
                        ((data.GlownyMatrixParameters?.KosztTechnicznySerwis
                          ?.Wartosc || 0) /
                          data.OkresUzytkowania) *
                        1.23
                      ).toFixed(2)}
                    </Typography>
                  </Grid>
                </Box>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    mb: 1,
                  }}
                >
                  <Grid size={{ xs: 6 }}>
                    <Typography
                      align="right"
                      variant="body2"
                      sx={{ pr: 2, fontSize: "0.8rem" }}
                    >
                      Opony:
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Typography
                      align="center"
                      variant="body2"
                      sx={{ fontSize: "0.8rem" }}
                    >
                      {(
                        (data.GlownyMatrixParameters?.KosztTechnicznyOpony
                          ?.Wartosc || 0) / data.OkresUzytkowania
                      ).toFixed(2)}
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Typography
                      align="center"
                      variant="body2"
                      sx={{ fontSize: "0.8rem" }}
                    >
                      {(
                        ((data.GlownyMatrixParameters?.KosztTechnicznyOpony
                          ?.Wartosc || 0) /
                          data.OkresUzytkowania) *
                        1.23
                      ).toFixed(2)}
                    </Typography>
                  </Grid>
                </Box>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    mb: 1,
                  }}
                >
                  <Grid size={{ xs: 6 }}>
                    <Typography
                      align="right"
                      variant="body2"
                      sx={{ pr: 2, fontSize: "0.8rem" }}
                    >
                      Samochód zastępczy:
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Typography
                      align="center"
                      variant="body2"
                      sx={{ fontSize: "0.8rem" }}
                    >
                      {(
                        (data.GlownyMatrixParameters
                          ?.KosztTechnicznySamochodZastepczy?.Wartosc || 0) /
                        data.OkresUzytkowania
                      ).toFixed(2)}
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Typography
                      align="center"
                      variant="body2"
                      sx={{ fontSize: "0.8rem" }}
                    >
                      {(
                        ((data.GlownyMatrixParameters
                          ?.KosztTechnicznySamochodZastepczy?.Wartosc || 0) /
                          data.OkresUzytkowania) *
                        1.23
                      ).toFixed(2)}
                    </Typography>
                  </Grid>
                </Box>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    mb: 1,
                  }}
                >
                  <Grid size={{ xs: 6 }}>
                    <Typography
                      align="right"
                      variant="body2"
                      sx={{ pr: 2, fontSize: "0.8rem" }}
                    >
                      Koszty dodatkowe (admin.: rej., sprzedaż, GSM):
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Typography
                      align="center"
                      variant="body2"
                      sx={{ fontSize: "0.8rem" }}
                    >
                      {(
                        (data.GlownyMatrixParameters?.KosztyDodatkowe
                          ?.Wartosc || 0) / data.OkresUzytkowania
                      ).toFixed(2)}
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 3 }}>
                    <Typography
                      align="center"
                      variant="body2"
                      sx={{ fontSize: "0.8rem" }}
                    >
                      {(
                        ((data.GlownyMatrixParameters?.KosztyDodatkowe
                          ?.Wartosc || 0) /
                          data.OkresUzytkowania) *
                        1.23
                      ).toFixed(2)}
                    </Typography>
                  </Grid>
                </Box>
              </Box>

              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  mb: 1,
                  mt: 2,
                }}
              >
                <Grid size={{ xs: 6 }}>
                  <Typography
                    align="right"
                    variant="body2"
                    sx={{ pr: 2, fontSize: "0.8rem", fontWeight: "bold" }}
                  >
                    Cena zakupu (BUDŻET):
                  </Typography>
                </Grid>
                <Grid size={{ xs: 3 }}>
                  <Typography
                    align="center"
                    variant="body2"
                    sx={{ fontSize: "0.8rem", fontWeight: "bold" }}
                  >
                    {data.CenaCennikowaNetto.toFixed(2)}
                  </Typography>
                </Grid>
                <Grid size={{ xs: 3 }}>
                  <Typography
                    align="center"
                    variant="body2"
                    sx={{ fontSize: "0.8rem", fontWeight: "bold" }}
                  >
                    {data.CenaCennikowa.toFixed(2)}
                  </Typography>
                </Grid>
              </Box>

              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  mb: 1,
                  mt: 2,
                }}
              >
                <Grid size={{ xs: 6 }}>
                  <Typography
                    align="right"
                    variant="body2"
                    sx={{ pr: 2, fontSize: "0.8rem" }}
                  >
                    Koszt dzienny:
                  </Typography>
                </Grid>
                <Grid size={{ xs: 3 }}>
                  <Typography
                    align="center"
                    variant="body2"
                    sx={{ fontSize: "0.8rem", fontWeight: "bold" }}
                  >
                    {(
                      (data.GlownyMatrixParameters?.KosztRazem?.Wartosc || 0) /
                      data.OkresUzytkowania /
                      30.4
                    ).toFixed(2)}
                  </Typography>
                </Grid>
                <Grid size={{ xs: 3 }}>
                  <Typography
                    align="center"
                    variant="body2"
                    sx={{ fontSize: "0.8rem", fontWeight: "bold" }}
                  >
                    {(
                      ((data.GlownyMatrixParameters?.KosztRazem?.Wartosc || 0) /
                        data.OkresUzytkowania /
                        30.4) *
                      1.23
                    ).toFixed(2)}
                  </Typography>
                </Grid>
              </Box>
            </Box>
          </AccordionDetails>
        </Accordion>
      </Box>

      {/* Parser Modal */}
      <Dialog
        open={isParserOpen}
        onClose={() => setIsParserOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Zrozum Ofertę (LLM)</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Wklej surowy tekst oferty, wyciąg z PDFa, maila lub strukturę JSON.
            Sztuczna inteligencja zmapuje dane bazowe, wyposażenie i cenniki.
          </Typography>
          <TextField
            autoFocus
            margin="dense"
            label="Treść oferty"
            fullWidth
            multiline
            rows={15}
            variant="outlined"
            value={parserText}
            onChange={(e) => setParserText(e.target.value)}
          />
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setIsParserOpen(false)} sx={{ color: "#666" }}>
            Anuluj
          </Button>
          <Button
            onClick={handleParseOffer}
            variant="contained"
            color="secondary"
            disabled={isParsing || !parserText.trim()}
          >
            {isParsing ? (
              <CircularProgress size={24} color="inherit" />
            ) : (
              "Analizuj i wstaw"
            )}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

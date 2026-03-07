import { useState, useEffect } from "react";
import axios from "axios";
import type { V1DataOption } from "../types";

export interface ControlCenterSettings {
  default_wibor: number;
  default_ltr_margin: number;
  default_depreciation_pct?: number;
  vat_rate?: number;
}

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
  InneKosztySerwisowania: 0.0,
  PakietSerwisowy: 0.0,
  PakietSerwisowyNazwa: null,
  KorektaRV: 0.0,
  KalkulacjaWolumenowa: null,
  WiborProcent: 0.0482,
  MarzaFinansowaProcent: 0.022,

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

export function useCalculator() {
  const [data, setData] = useState<V1DataOption>(INITIAL_DATA);
  const [expanded, setExpanded] = useState<string | false>("panel1");
  const [isParserOpen, setIsParserOpen] = useState(false);
  const [parserText, setParserText] = useState("");
  const [isParsing, setIsParsing] = useState(false);

  useEffect(() => {
    fetchSettings();
    const params = new URLSearchParams(window.location.search);
    const id = params.get("id");
    if (id) {
      loadKalkulacja(id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchSettings = async () => {
    try {
      const resp = await axios.get<ControlCenterSettings>(
        "http://127.0.0.1:8000/api/control-center",
      );
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
  const handleUpdateFactoryOption = (id: number, field: string, value: any) => {
    setData((prev) => ({
      ...prev,
      OpcjeFabryczne: prev.OpcjeFabryczne.map((opt) =>
        opt.Id === id ? { ...opt, [field]: value } : opt
      ),
    }));
  };

  const handleAddFactoryOption = () => {
    setData((prev) => {
      const nextId =
        prev.OpcjeFabryczne.length > 0
          ? Math.max(...prev.OpcjeFabryczne.map((o) => o.Id)) + 1
          : 1;
      return {
        ...prev,
        OpcjeFabryczne: [
          ...prev.OpcjeFabryczne,
          {
            Id: nextId,
            Nazwa: "Nowa opcja",
            CenaNetto: 0,
            Cena: 0,
            isNierabatowany: false,
            WR: false,
          },
        ],
      };
    });
  };

  const handleRemoveFactoryOption = (id: number) => {
    setData((prev) => ({
      ...prev,
      OpcjeFabryczne: prev.OpcjeFabryczne.filter((opt) => opt.Id !== id),
    }));
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleUpdateServiceOption = (id: number, field: string, value: any) => {
    setData((prev) => ({
      ...prev,
      OpcjeSerwisowe: prev.OpcjeSerwisowe.map((opt) =>
        opt.Id === id ? { ...opt, [field]: value } : opt
      ),
    }));
  };

  const handleAddServiceOption = () => {
    setData((prev) => {
      const nextId =
        prev.OpcjeSerwisowe.length > 0
          ? Math.max(...prev.OpcjeSerwisowe.map((o) => o.Id)) + 1
          : 1;
      return {
        ...prev,
        OpcjeSerwisowe: [
          ...prev.OpcjeSerwisowe,
          {
            Id: nextId,
            Nazwa: "Nowa usługa",
            CenaNetto: 0,
            Cena: 0,
            isNierabatowany: false,
            WR: false,
          },
        ],
      };
    });
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleAddExtractedServiceOption = (extracted: any) => {
    setData((prev) => {
      const nextId =
        prev.OpcjeSerwisowe.length > 0
          ? Math.max(...prev.OpcjeSerwisowe.map((o) => o.Id)) + 1
          : 1;
      const vat = prev.StawkaVat || 0.23;
      return {
        ...prev,
        OpcjeSerwisowe: [
          ...prev.OpcjeSerwisowe,
          {
            Id: nextId,
            Nazwa: extracted.name,
            CenaNetto: extracted.net_price,
            Cena: extracted.net_price * (1 + vat),
            isNierabatowany: false,
            WR: false,
          },
        ],
      };
    });
  };

  const handleRemoveServiceOption = (id: number) => {
    setData((prev) => ({
      ...prev,
      OpcjeSerwisowe: prev.OpcjeSerwisowe.filter((opt) => opt.Id !== id),
    }));
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const applyParsedOffer = (parsedRaw: any, numer_kalkulacji?: string) => {
    let parsed = parsedRaw;

    if (parsedRaw && parsedRaw.card_summary && !parsedRaw.factory_options) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const parsePrice = (val: any) => {
        if (typeof val === "number") return val;
        if (!val) return 0;
        let s = String(val).replace(/\s/g, "").replace(/[^\d,.-]/g, "");
        if (s.includes(".") && s.includes(",")) s = s.replace(/\./g, "");
        s = s.replace(",", ".");
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
          for (const s of p.sections || []) {
            if (s.data && Array.isArray(s.data)) {
              for (const item of s.data) {
                if (item.category === "Rabat" || item.item === "Rabat") {
                  discountAmt = parsePrice(item.price_net || item.price || 0);
                }
              }
            }
          }
        }
      } catch (e) {
        console.error(e);
      }

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
        fuel_type: "Diesel",
        body_style: cs.body_style || "",
        samar_category: "KLASYFIKACJA...",
        power_hp: parsedRaw.digital_twin?.technical_data?.power_hp || "",
        vehicle_class: cs.vehicle_class || "",
        manual_wr_correction: cs.manual_wr_correction || 0,
      };
    }

    setData((prev) => {
      const vat = prev.StawkaVat || 0.23;

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

      let opony = prev.RozmiarOpon;
      let klasaOpon = prev.KlasaOpon;
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

          const diameter = parseInt(match[4], 10);
          if (parsed.vehicle_class === "Dostawczy") {
            klasaOpon = "WZMOCNIONE";
          } else {
            if (diameter <= 16) klasaOpon = "BUDGET";
            else if (diameter >= 17 && diameter <= 18) klasaOpon = "MEDIUM";
            else if (diameter >= 19) klasaOpon = "PREMIUM";
          }
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
        OpcjeFabryczne: newFactoryOptions,
        OpcjeSerwisowe: newServiceOptions,
        HomologacjaSelected: parsed.vehicle_class || prev.HomologacjaSelected,
        TypRabatu: "Kwotowo",
        RabatKwotaNetto: rabatKwotaNetto,
        RabatKwota: rabatKwota,
        RabatProcent: rabatProcent,
        RozmiarOpon: opony,
        KlasaOpon: klasaOpon,
        KorektaRV: parsed.manual_wr_correction || 0,
      };
    });

    const classificationBrand = parsedRaw.brand || parsed.brand || "";
    const classificationModel = parsedRaw.model || parsed.model || "";
    const classificationBody =
      parsedRaw.card_summary?.body_style || parsed.body_style || parsed.trim || "";

    if (classificationBrand || classificationModel) {
      axios
        .post("http://127.0.0.1:8000/api/parse-offer/samar-category", {
          brand: classificationBrand,
          model: classificationModel,
          body_style: classificationBody || "",
        })
        .then((resp) => {
          if (resp.data?.samar_category) {
            setData((prev) => ({
              ...prev,
              KategoriaSamar: resp.data.samar_category,
            }));
          }
        })
        .catch((err) => {
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

  const handleChangeTypRabatu = (typ: string) => {
    if (typ !== "Procentowo" && typ !== "Kwotowo") return;
    setData((prev) => {
      return { ...prev, TypRabatu: typ as "Procentowo" | "Kwotowo" };
    });
  };

  return {
    data,
    setData,
    expanded,
    isParserOpen,
    setIsParserOpen,
    parserText,
    setParserText,
    isParsing,
    handleChange,
    handleUpdate,
    handleUpdateNetto,
    handleUpdateBrutto,
    handleUpdateRabat,
    handleUpdateFactoryOption,
    handleAddFactoryOption,
    handleRemoveFactoryOption,
    handleUpdateServiceOption,
    handleAddServiceOption,
    handleAddExtractedServiceOption,
    handleRemoveServiceOption,
    handleParseOffer,
    handleChangeTypRabatu,
  };
}

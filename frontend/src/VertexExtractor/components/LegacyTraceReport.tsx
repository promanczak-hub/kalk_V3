import { useMemo, useState } from "react";
import { X } from "lucide-react";
import type {
  PipelineData,
  PipelineStep,
} from "./VehicleTableParts/calculations/useVehicleCalculations";

interface Props {
  data: PipelineData;
  onClose: () => void;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

// ── Legacy-style PL number formatting (always 4 decimals, comma) ──────────
const fmt4 = (v: Any): string => {
  if (v === null || v === undefined || v === "") return "";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n
    .toLocaleString("en-US", {
      minimumFractionDigits: 4,
      maximumFractionDigits: 4,
      useGrouping: false,
    })
    .replace(".", ",");
};

const fmtBool = (v: Any) => (v ? "v" : "");

const fmtInt = (v: Any): string => {
  if (v === null || v === undefined || v === "") return "";
  return String(v);
};

const fmtDateNow = (): string => {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};

// ── Trace helpers ──────────────────────────────────────────────────────────
const findStep = (steps: PipelineStep[], n: number): PipelineStep | undefined =>
  steps.find((s) => s.step === n);

const traceItems = (step?: PipelineStep) => {
  if (!step?.trace) return [] as Array<{ krok: string; rownanie?: string; wynik: Any }>;
  return step.trace
    .map((t) => (typeof t === "string" ? { krok: t, wynik: null } : t))
    .filter((t) => !!t.krok);
};

// ── Raw legacy section: 2-column table ─────────────────────────────────────
function LegacyTable({
  title,
  rows,
  colspan = 2,
}: {
  title?: string;
  rows: Array<[string, string, boolean?]>;
  colspan?: number;
}) {
  return (
    <>
      <table style={legacyTableStyle}>
        <tbody>
          {title && (
            <tr>
              <td colSpan={colspan} style={tdStyle}>
                <b>{title}</b>
              </td>
            </tr>
          )}
          {rows.map(([label, value, bold], i) => (
            <tr key={i}>
              <td style={tdStyle}>{bold ? <b>{label}</b> : label}</td>
              <td style={tdStyle}>{bold ? <b>{value}</b> : value}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <br />
    </>
  );
}

// ── Raw legacy matrix table (multi-column, e.g. 7-year insurance, 48-mc schedule) ─
function LegacyMatrix({
  title,
  columns,
  rows,
  titleColSpan,
}: {
  title?: string;
  columns: string[];
  rows: Array<{ label: string; values: string[]; bold?: boolean }>;
  titleColSpan?: number;
}) {
  const span = titleColSpan ?? columns.length + 1;
  return (
    <>
      <table style={legacyTableStyle}>
        <tbody>
          {title && (
            <tr>
              <td colSpan={span} style={tdStyle}>
                {title}
              </td>
            </tr>
          )}
          <tr>
            <td style={tdStyle}></td>
            {columns.map((c, i) => (
              <td key={i} style={tdStyle}>
                {c}
              </td>
            ))}
          </tr>
          {rows.map((r, i) => (
            <tr key={i}>
              <td style={tdStyle}>{r.bold ? <b>{r.label}</b> : r.label}</td>
              {r.values.map((v, j) => (
                <td key={j} style={tdStyle}>
                  {r.bold ? <b>{v}</b> : v}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <br />
    </>
  );
}

const legacyTableStyle: React.CSSProperties = {
  borderCollapse: "collapse",
  fontFamily: "Verdana, Arial, sans-serif",
  fontSize: "12px",
  color: "#000",
  background: "#fff",
};

const tdStyle: React.CSSProperties = {
  border: "1px solid #000",
  padding: "1px 4px",
  verticalAlign: "top",
  whiteSpace: "nowrap",
};

// ── Main component ────────────────────────────────────────────────────────
export function LegacyTraceReport({ data, onClose }: Props) {
  const [view, setView] = useState<"diagnostyka" | "pipeline" | "json">("diagnostyka");
  const steps = data.steps;
  const payload = data.payload || {};

  const s1 = findStep(steps, 1); // Opony
  const s2 = findStep(steps, 2); // Koszty Dodatkowe
  const s3 = findStep(steps, 3); // Samochód Zastępczy
  const s4 = findStep(steps, 4); // Serwis
  const s5 = findStep(steps, 5); // Cena Zakupu (CAPEX)
  const s6 = findStep(steps, 6); // Utrata Wartości (WR)
  const s7 = findStep(steps, 7); // Amortyzacja
  const s8 = findStep(steps, 8); // Ubezpieczenie
  const s9 = findStep(steps, 9); // Finanse
  const s10 = findStep(steps, 10); // Koszt Dzienny
  const s11 = findStep(steps, 11); // Stawka
  const s12 = findStep(steps, 12); // Budżet Marketingowy

  // ── Derived values ───────────────────────────────────────────────────────
  const months = data.months;
  const oferowanaStawka = Number(s11?.outputs?.oferowana_stawka || 0);
  const kosztMc = Number(s10?.outputs?.koszt_mc || 0);
  const kosztMcBez = Number(s10?.outputs?.koszt_mc_bez_czynszu || 0);
  const kosztyOgolem = Number(s10?.outputs?.koszty_ogolem || 0);
  const marzaMc = Number(s11?.outputs?.marza_mc || 0);
  const marzaNaKontrakcie = Number(s11?.outputs?.marza_na_kontrakcie || 0);
  const marzaProcent = Number(payload.pricing_margin_pct || 0) / 100;
  const przychod = oferowanaStawka * months;

  const kosztFinansowy = Number(s9?.outputs?.koszt_finansowy || 0);
  const utrataNetto = Number(s6?.outputs?.utrata_z_czynszem || 0);
  const wrNetto = Number(s6?.outputs?.vr_samar || 0);
  const wpAmort = Number(s6?.outputs?.wp_amortyzacja || 0);
  const basePriceFull = Number(s6?.outputs?.base_price_net_full || 0);
  const rvDebug = (s6?.outputs?.rv_debug || {}) as Record<string, Any>;

  const serwisTotal = Number(s4?.outputs?.service_total || 0);
  const oponyTotal = Number(s1?.outputs?.tires_total || 0);
  const insuranceTotal = Number(s8?.outputs?.insurance_total || 0);
  const additionalTotal = Number(s2?.outputs?.additional_costs_total || 0);
  const rcTotal = Number(s3?.outputs?.rc_total || 0);
  const capexFin = Number(s5?.outputs?.capex_for_financing || 0);
  const kosztDzienny = Number(s10?.outputs?.koszt_dzienny || 0);

  // Finance fields
  const wartoscPoczatkowaNetto = Number(s9?.outputs?.wartosc_poczatkowa_netto || capexFin);
  const wartoscKredytu = Number(s9?.outputs?.wartosc_kredytu || capexFin);
  const czynszInicjalnyNetto = Number(s9?.outputs?.czynsz_inicjalny || 0);
  const czynszInicjalnyProcent = Number(s9?.outputs?.czynsz_procent || 0);
  const wykupKwota = Number(s9?.outputs?.wykup_kwota || 0);
  const oprocentowanie = Number(s9?.outputs?.oprocentowanie || 0);
  const wibor = Number(payload.wibor_pct || 0) / 100;
  const marzaFinansowa = Number(payload.margin_pct || 0) / 100;
  const rataKwotaPmt = Number(s9?.outputs?.monthly_pmt_z_czynszem || 0);
  const rataKwotaPmtBez = Number(s9?.outputs?.monthly_pmt_bez_czynszu || 0);
  const rataProcent = Number(s9?.outputs?.rata_procent || 0);
  const wykupProcent = capexFin ? wykupKwota / capexFin : 0;
  const sumaOdsetekZ = kosztFinansowy;
  const sumaOdsetekBez = Number(s9?.outputs?.suma_odsetek_bez_czynszu || 0);
  const ratyZ = (s9?.outputs?.raty_z_czynszem || []) as Array<Record<string, Any>>;
  const ratyBez = (s9?.outputs?.raty_bez_czynszu || []) as Array<Record<string, Any>>;

  // Amortyzacja
  const procentAmortMiesiecznie = Number(s7?.outputs?.procent_amortyzacji_miesiecznie || 0);
  const kwotaAmort1Mc = months ? (wpAmort - wrNetto) / months : 0;

  // Tires breakdown from trace
  const tiresTrace = traceItems(s1);
  const oponyHardware = Number(
    tiresTrace.find((t) => /hardware|kompl/.test(t.krok || ""))?.wynik || 0
  );
  const oponyStorage = Number(
    tiresTrace.find((t) => /przechowywani/.test(t.krok || ""))?.wynik || 0
  );
  const oponySwaps = Number(
    tiresTrace.find((t) => /przekładk|swap/i.test(t.krok || ""))?.wynik || 0
  );
  const oponyOdkup = Number(
    tiresTrace.find((t) => /odkup/i.test(t.krok || ""))?.wynik || 0
  );

  // Service threshold table (segments from trace)
  const serviceTrace = traceItems(s4);
  const serviceSegments = serviceTrace.filter((t) => /Serwis:\s*(Segment|Ostatni)/.test(t.krok));

  // Additional costs items from trace
  const addTrace = traceItems(s2);

  // Service input + samar id
  const serviceInput = (s4?.inputs?.service_input || {}) as Record<string, Any>;
  const samarClassId =
    serviceInput.samar_class_id ||
    s3?.inputs?.klasa_id ||
    s8?.outputs?.klasa_id ||
    "?";

  // Replacement car
  const rcRate = Number(s3?.inputs?.rc_rate || 0);
  const rcEnabled = !!s3?.inputs?.enabled;
  const rcKlasaId = s3?.inputs?.klasa_id || "?";

  // Insurance year-breakdown (matrix)
  const insYearBreakdown =
    (s8?.outputs?.year_breakdown || []) as Array<Record<string, Any>>;
  const insWspSredniPrzebieg = Number(s8?.outputs?.wsp_sredni_przebieg || 0);
  const insWspWartoscSzkody = Number(s8?.outputs?.wsp_wartosc_szkody || 0);

  // Cena zakupu brutto chain
  const vatRate = 1.23;
  const vehicleCapex = Number(s5?.inputs?.vehicle_capex || 0);
  const tiresCapex = Number(s5?.inputs?.tires_capex || 0);
  const optionsCapex = Number(s5?.inputs?.options_capex || 0);
  const discountPct = Number(payload.discount_pct || 0) / 100;
  const cenaKatalogowaBrutto = basePriceFull * vatRate;
  const factoryOptionsSumNet = (payload.factory_options || []).reduce(
    (s: number, o: { price_net?: number }) => s + (o.price_net || 0),
    0
  );
  const opcjeFabryczneBrutto = factoryOptionsSumNet * vatRate;
  const cenaKatalogowaZOpcjamiBrutto = cenaKatalogowaBrutto + opcjeFabryczneBrutto;
  const cenaPoRabacieBrutto = cenaKatalogowaZOpcjamiBrutto * (1 - discountPct);
  const rabatKwotowoBrutto = cenaKatalogowaZOpcjamiBrutto - cenaPoRabacieBrutto;
  const rabatKwotowoNetto = rabatKwotowoBrutto / vatRate;
  const opcjeSerwisoweBrutto = optionsCapex * vatRate;
  const tiresCapexBrutto = tiresCapex * vatRate;
  const tiresCount = Number(s1?.outputs?.IloscOpon || 0);
  const cenaZa1KompletBrutto = tiresCount > 0 ? tiresCapexBrutto / tiresCount : 0;

  // Service options sum with include_in_wr
  const opcjeZwrSum = (payload.service_options || [])
    .filter((o: { include_in_wr?: boolean }) => o.include_in_wr)
    .reduce(
      (s: number, o: { price_net?: number }) => s + (o.price_net || 0),
      0
    );

  // Lacny koszt finansowy/techniczny
  const lacznyKosztFinansowy = utrataNetto + kosztFinansowy;
  const lacznyKosztTechniczny =
    serwisTotal + oponyTotal + insuranceTotal + additionalTotal + rcTotal;

  // Model display string
  const brandStr = String(payload.brand || payload.engine_name || "-");
  const modelStr = String(payload.model || payload.brand_model || "-");
  const samarCat = String(payload.samar_category || "-");

  const jsonText = useMemo(() => JSON.stringify(steps, null, 2), [steps]);

  // ── Rozkład marży 6-składowych ───────────────────────────────────────────
  const rozkladComponents = [
    {
      label: "Koszt finansowy",
      koszty: utrataNetto + kosztFinansowy,
      baseMc: months ? (utrataNetto + kosztFinansowy) / months : 0,
    },
    {
      label: "Ubezpieczenie",
      koszty: insuranceTotal,
      baseMc: Number(s8?.outputs?.insurance_base || 0),
    },
    {
      label: "Samochód zastępczy",
      koszty: rcTotal,
      baseMc: Number(s3?.outputs?.rc_base || 0),
    },
    {
      label: "Serwis",
      koszty: serwisTotal,
      baseMc: Number(s4?.outputs?.service_base || 0),
    },
    {
      label: "Opony",
      koszty: oponyTotal,
      baseMc: months ? oponyTotal / months : 0,
    },
    {
      label: "Serwis admin rej",
      koszty: additionalTotal,
      baseMc: Number(s2?.outputs?.additional_costs_base || 0),
    },
  ];
  const sumRozkladKoszty = rozkladComponents.reduce((a, c) => a + c.koszty, 0);

  return (
    <div className="fixed inset-0 z-[9999] flex flex-col bg-white">
      {/* Minimal top bar — legacy-style window title */}
      <div className="flex items-center justify-between px-3 py-1 border-b border-slate-300 bg-white text-xs">
        <div style={{ fontFamily: "Verdana, Arial, sans-serif", fontSize: "13px", color: "#000" }}>
          Diagnostyka przeliczenie na dziś
        </div>
        <div className="flex items-center gap-1 text-[10px] text-slate-500">
          <button
            onClick={() => setView("diagnostyka")}
            className={`px-1.5 py-0.5 ${view === "diagnostyka" ? "underline font-bold text-slate-900" : "hover:text-slate-700"}`}
          >
            diagnostyka
          </button>
          <span>·</span>
          <button
            onClick={() => setView("pipeline")}
            className={`px-1.5 py-0.5 ${view === "pipeline" ? "underline font-bold text-slate-900" : "hover:text-slate-700"}`}
          >
            pipeline
          </button>
          <span>·</span>
          <button
            onClick={() => setView("json")}
            className={`px-1.5 py-0.5 ${view === "json" ? "underline font-bold text-slate-900" : "hover:text-slate-700"}`}
          >
            json
          </button>
          <button
            onClick={onClose}
            className="ml-2 p-1 hover:bg-slate-200"
            aria-label="Zamknij"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-auto p-3 bg-white">
        {view === "diagnostyka" ? (
          <div style={{ fontFamily: "Verdana, Arial, sans-serif", fontSize: "12px", color: "#000" }}>
            {/* GŁÓWNE PARAMETRY */}
            <LegacyTable
              title={`GŁÓWNE PARAMETRY (${data.vehicle_id?.slice(0, 8) || ""})`}
              rows={[
                ["Data utworzenia", fmtDateNow()],
                ["OkresUzytkowania", fmtInt(months)],
                ["Przebieg", fmtInt(payload.przebieg_bazowy)],
                ["Produkt", "LTR"],
                ["Rocznik", payload.vehicle_vintage === "current" ? "bieżący" : String(payload.vehicle_vintage || "bieżący")],
                ["Marka", brandStr],
                ["Model", modelStr],
                ["Symbol E-tax", samarCat],
                ["Nadwozie", String(payload.body_type_name || "-")],
                ["Marża", fmt4(marzaProcent)],
                ["CzynszInicjalny", fmt4(payload.CzynszKwota || 0)],
                ["CenaCennikowa", fmt4(payload.base_price_net)],
                ["Opcje fabryczne (suma)", fmt4(factoryOptionsSumNet)],
                ["CzyMetalik", fmtBool(payload.is_metalic)],
                ["LakierMetalik", fmt4(0)],
                ["Rabat %", fmt4(discountPct)],
                ["Rabat kwotowo", fmt4(rabatKwotowoNetto)],
                ["Homologacja", "Osobowy"],
                ["Opcje z WR (suma)", fmt4(opcjeZwrSum)],
                ["PakietSerwisowy", fmt4(payload.pakiet_serwisowy)],
                ["InneKosztySerwisowaniaKwota", fmt4(payload.inne_koszty_serwisowania_netto)],
                ["KorektaWR", fmt4(payload.manual_wr_correction)],
                ["ZOponami", fmtBool(payload.z_oponami)],
                ["Rozmiar opon", fmtInt(payload.srednica_felgi)],
                ["KlasaOpon", String(payload.klasa_opony_string || "").toUpperCase()],
                ["LiczbaKompletowOpon", fmt4(payload.liczba_kompletow_opon || 0)],
                ["SamochodZastepczy", fmtBool(payload.replacement_car_enabled)],
                ["NaukaJazdy", ""],
                ["ExpressPlaciUbezpieczenie", "v"],
                ["DoubezpieczenieKradziezy", ""],
                ["CzyDemontazKraty", fmtBool(payload.add_grid_dismantling)],
                ["CzyHak", fmtBool(payload.add_hook_installation)],
                ["CzyGPS", fmtBool(payload.add_gsm_subscription)],
              ]}
            />

            {/* WYNIK NETTO */}
            <LegacyTable
              title="WYNIK NETTO"
              rows={[
                ["Cena zakupu", fmt4(capexFin)],
                ["Serwis", fmt4(serwisTotal)],
                ["Opony", fmt4(oponyTotal)],
                ["Ubezpieczenie", fmt4(insuranceTotal)],
                ["Koszty dodatkowe", fmt4(additionalTotal)],
                ["Samochód zastępczy", fmt4(rcTotal)],
                ["Finansowe", fmt4(kosztFinansowy)],
                ["Utrata wartości", fmt4(utrataNetto)],
                ["Koszt dzienny", fmt4(kosztDzienny)],
                ["Marza na kontrakcie", fmt4(marzaNaKontrakcie)],
                ["Oferowana stawka", fmt4(oferowanaStawka)],
                ["Przychód", fmt4(przychod)],
              ]}
            />

            {/* OPONY */}
            <LegacyTable
              title="OPONY"
              rows={[
                ["iloscOponNaKontrakt", fmt4(tiresCount)],
                ["koszt1kompletu", fmt4(s1?.outputs?.Koszt1KplOpon || 0)],
                ["lacznyKosztOpon", fmt4(oponyHardware)],
                ["cenaPrzekladki", fmt4(oponySwaps)],
                ["przechowywanieOpon", fmt4(oponyStorage)],
                ["odkupOpon", fmt4(oponyOdkup)],
                ["opony", fmt4(oponyTotal), true],
              ]}
            />

            {/* KOSZTY DODATKOWE */}
            <LegacyTable
              title="KOSZTY DODATKOWE"
              rows={[
                ...addTrace.map(
                  (t) => [t.krok, fmt4(t.wynik)] as [string, string]
                ),
                ["kosztyDodatkowe", fmt4(additionalTotal), true],
              ]}
            />

            {/* SAMOCHÓD ZASTĘPCZY */}
            <LegacyTable
              title="SAMOCHÓD ZASTĘPCZY"
              rows={[
                ["klasaId", fmtInt(rcKlasaId)],
                ["klasa", String(s3?.inputs?.klasa_name || "-")],
                ["sredniaIloscDobWRoku", fmt4(s3?.inputs?.srednia_dob_w_roku || 6.5)],
                ["dobaNetto", fmt4(s3?.inputs?.doba_netto || rcRate)],
                ["okresUzytkowania", fmt4(months)],
                ["stawkaZaZastepczy", rcEnabled ? fmt4(rcTotal) : fmt4(0), true],
              ]}
            />

            {/* Tabela serwisowa (progi km × kwoty) */}
            {serviceSegments.length > 0 && (
              <LegacyTable
                title="Tabela serwisowa"
                rows={[
                  ["Model Id", fmt4(samarClassId)],
                  ...serviceSegments.map((t) => {
                    // krok: "Serwis: Segment 0 - 30000 km" → "30000"
                    const m = t.krok.match(/(\d+)\s*km/);
                    const progLabel = m ? m[1] : t.krok;
                    return [progLabel, fmt4(t.wynik)] as [string, string];
                  }),
                ]}
              />
            )}

            {/* SERWIS */}
            <LegacyTable
              title="SERWIS"
              rows={[
                ["sumaZKosztowPrzebiegu", fmt4(s4?.outputs?.service_base_unmultiplied || s4?.outputs?.service_total || serwisTotal)],
                ["wynajemWLatach", fmt4(months / 12)],
                ["iloscPrzegladowZPrzebiegu", fmt4(serviceSegments.length)],
                ["inneKosztySerwisowaniaNetto", fmt4(serviceInput.inne_koszty_serwisowania_netto || 0)],
                ["kosztyLaczneZPrzebiegiemPodstawowym", fmt4(serwisTotal)],
                ["korektaAdminProcent", fmt4(s4?.outputs?.korekta_admin_proc || 0)],
                ["pakietSerwisowyKorektaKosztow", fmt4(serviceInput.pakiet_serwisowy || 0)],
                ["kosztyLacznie", fmt4(serwisTotal), true],
              ]}
            />

            {/* CENA ZAKUPU (brutto) */}
            <LegacyTable
              title="CENA ZAKUPU (wartości brutto)"
              rows={[
                ["opcjeFabryczneSuma", fmt4(opcjeFabryczneBrutto)],
                ["cenaKatalogowaZOpcjamiFabrycznymi", fmt4(cenaKatalogowaZOpcjamiBrutto)],
                ["oplataTransportowa", fmt4(0)],
                ["opcjeKatalogoweNierabatowane", fmt4(0)],
                ["cenaKatalogowaZOPcjamiFabrycznymiPoRabacie", fmt4(cenaPoRabacieBrutto)],
                ["rabatKwotowo", fmt4(rabatKwotowoBrutto)],
                ["opcjeSerwisowe", fmt4(opcjeSerwisoweBrutto)],
                ["cenaZa1KompletOpon", fmt4(cenaZa1KompletBrutto)],
                ["pakietSerwisowy", fmt4(payload.pakiet_serwisowy || 0)],
                [
                  "cenaSamochoduZOponamiIOpcjamiSerwisowymiIPakiet",
                  fmt4(capexFin * vatRate),
                  true,
                ],
                ["cenaSamochoduBezOpon", fmt4((vehicleCapex + optionsCapex) * vatRate)],
                ["cenaSamochoduBezOponIOpcjiSerwisowych", fmt4(vehicleCapex * vatRate)],
                ["cenaSamochoduBezOpon_OpcjiSerwisowych_iPakietu", fmt4(vehicleCapex * vatRate)],
              ]}
            />

            {/* UTRATA WARTOŚCI (NOWA) */}
            <LegacyTable
              title="UTRATA WARTOŚCI (NOWA)"
              rows={[
                [
                  "Łączna cena zakupu (netto)",
                  fmt4(basePriceFull + (rvDebug.options_net_full ?? factoryOptionsSumNet)),
                ],
                ["Łączna cena zakupu po rabacie (netto)", fmt4(wpAmort)],
                ["WR (netto)", fmt4(wrNetto)],
                ["WR %", fmt4(wpAmort > 0 ? (wrNetto / wpAmort) * 100 : 0)],
                ["WR dla LO (netto)", fmt4(rvDebug.wr_lo_net ?? 0)],
                ["Utrata wartości (netto)", fmt4(utrataNetto), true],
                ["Utrata wartości z czynszem inicjalnym (netto)", fmt4(s6?.outputs?.utrata_z_czynszem || 0)],
                ["KorektaZaPrzebiegKwotowo (netto)", fmt4(rvDebug.krok4_korekta_przebieg_netto ?? 0)],
                ["KorektaAdministracyjnaKwotowo (netto)", fmt4(0)],
              ]}
            />

            {/* AMORTYZACJA */}
            <LegacyTable
              title="AMORTYZACJA"
              rows={[
                ["WP", fmt4(wpAmort)],
                ["WR", fmt4(wrNetto)],
                ["utrataWartosci", fmt4(wpAmort - wrNetto)],
                ["kwotaAmortyzacji1Miesiac", fmt4(kwotaAmort1Mc)],
                ["procentAmortyzacji", fmt4(procentAmortMiesiecznie)],
              ]}
            />

            {/* UBEZPIECZENIE — matrix 7-lat */}
            {insYearBreakdown.length > 0 && (
              <LegacyMatrix
                title="UBEZPIECZENIE"
                titleColSpan={8}
                columns={insYearBreakdown.map((y) => fmtInt(y.rok))}
                rows={[
                  {
                    label: "PostawaNaliczania",
                    values: insYearBreakdown.map((y) => fmt4(y.PostawaNaliczania)),
                  },
                  {
                    label: "SkladkaBazowaAC",
                    values: insYearBreakdown.map((y) => fmt4(y.SkladkaBazowaAC)),
                  },
                  {
                    label: "SkladkaAC",
                    values: insYearBreakdown.map((y) => fmt4(y.SkladkaAC)),
                  },
                  {
                    label: "SkladkaOC",
                    values: insYearBreakdown.map((y) => fmt4(y.SkladkaOC)),
                  },
                  {
                    label: "DoubezpieczenieKradziezy",
                    values: insYearBreakdown.map((y) => fmt4(y.DoubezpieczenieKradziezy)),
                  },
                  {
                    label: "DoubezpieczenieNaukaJazdu",
                    values: insYearBreakdown.map((y) => fmt4(y.DoubezpieczenieNaukaJazdy)),
                  },
                  {
                    label: "SkladkaRoczna",
                    values: insYearBreakdown.map((y) => fmt4(y.SkladkaRoczna)),
                  },
                  {
                    label: "SredniaWartoscSzkodyRocznie",
                    values: insYearBreakdown.map((y) => fmt4(y.SredniaWartoscSzkodyRocznie)),
                  },
                  {
                    label: "SkladkaLacznie",
                    values: insYearBreakdown.map((y) => fmt4(y.SkladkaLacznie)),
                  },
                  {
                    label: "SkladkaWCalymOkresie",
                    values: insYearBreakdown.map((y) => fmt4(y.SkladkaWCalymOkresie)),
                  },
                ]}
              />
            )}

            {/* sredniaWartoscSzkody */}
            <LegacyTable
              title="sredniaWartoscSzkody"
              rows={[
                ["klasaId", fmtInt(samarClassId)],
                ["klasa", String(s3?.inputs?.klasa_name || "-")],
                ["wspSredniPrzebieg", fmt4(insWspSredniPrzebieg)],
                ["WspWartoscSzkody", fmt4(insWspWartoscSzkody)],
              ]}
            />

            {/* FINANSOWE */}
            <LegacyTable
              title="FINANSOWE"
              rows={[
                ["WartoscPoczatkowaNetto", fmt4(wartoscPoczatkowaNetto)],
                ["wartoscKredytu", fmt4(wartoscKredytu)],
                ["czynszInicjalnyProcent", fmt4(czynszInicjalnyProcent)],
                ["wykupProcent", fmt4(wykupProcent)],
                ["wykupKwota", fmt4(wykupKwota)],
                ["iloscRat", fmtInt(months)],
                ["wibor", fmt4(wibor)],
                ["marzaFinansowa", fmt4(marzaFinansowa)],
                ["oprocentowanie", fmt4(oprocentowanie)],
              ]}
            />

            {/* rataProcent / rataKwota (Z) */}
            <LegacyTable
              rows={[
                ["rataProcent", fmt4(rataProcent)],
                ["rataKwota", fmt4(rataKwotaPmt)],
              ]}
            />

            {/* HARMONOGRAM Z czynszem inicjalnym */}
            {ratyZ.length > 0 && (
              <LegacyMatrix
                columns={ratyZ.map((r) => fmtInt(r.NumerRaty))}
                rows={[
                  {
                    label: "Kapitał do spłaty",
                    values: ratyZ.map((r) => fmt4(r.KapitalDoSplaty)),
                  },
                  {
                    label: "Rata leasingowa",
                    values: ratyZ.map((r) => fmt4(r.RataLeasingowa)),
                  },
                  {
                    label: "Rata kapitalowa",
                    values: ratyZ.map((r) => fmt4(r.RataKapitalowa)),
                  },
                  {
                    label: "Kapitał po spłacie",
                    values: ratyZ.map((r) => fmt4(r.KapitalPoSplacie)),
                  },
                  {
                    label: "Rata odsetkowa",
                    values: ratyZ.map((r) => fmt4(r.RataOdsetkowa)),
                  },
                ]}
              />
            )}

            <LegacyTable
              rows={[
                ["Suma odsetek z czynszem inicjalnym (min WR/WK)", fmt4(sumaOdsetekZ)],
              ]}
            />

            {/* rataProcent / rataKwota (BEZ) */}
            <LegacyTable
              rows={[
                ["rataProcent", fmt4(rataProcent)],
                ["rataKwota", fmt4(rataKwotaPmtBez || rataKwotaPmt)],
              ]}
            />

            {/* HARMONOGRAM BEZ czynszu inicjalnego */}
            {ratyBez.length > 0 && (
              <LegacyMatrix
                columns={ratyBez.map((r) => fmtInt(r.NumerRaty))}
                rows={[
                  {
                    label: "Kapitał do spłaty",
                    values: ratyBez.map((r) => fmt4(r.KapitalDoSplaty)),
                  },
                  {
                    label: "Rata leasingowa",
                    values: ratyBez.map((r) => fmt4(r.RataLeasingowa)),
                  },
                  {
                    label: "Rata kapitalowa",
                    values: ratyBez.map((r) => fmt4(r.RataKapitalowa)),
                  },
                  {
                    label: "Kapitał po spłacie",
                    values: ratyBez.map((r) => fmt4(r.KapitalPoSplacie)),
                  },
                  {
                    label: "Rata odsetkowa",
                    values: ratyBez.map((r) => fmt4(r.RataOdsetkowa)),
                  },
                ]}
              />
            )}

            <LegacyTable
              rows={[["Suma odsetek bez czynszu inicjalnego", fmt4(sumaOdsetekBez)]]}
            />

            {/* KOSZT DZIENNY */}
            <LegacyMatrix
              title="KOSZT DZIENNY"
              titleColSpan={3}
              columns={["NETTO", "KOSZTY SYMULOWANE (BEZ UWZGLDĘDNIENIA CZ.INICJALNEGO)"]}
              rows={[
                {
                  label: "lacznyKosztFinansowy",
                  values: [fmt4(lacznyKosztFinansowy), fmt4(lacznyKosztFinansowy)],
                },
                {
                  label: "lacznyKosztTechniczny",
                  values: [fmt4(lacznyKosztTechniczny), fmt4(lacznyKosztTechniczny)],
                },
                {
                  label: "kosztyOgolem",
                  values: [
                    fmt4(kosztyOgolem),
                    fmt4(kosztMcBez ? kosztMcBez * months : kosztyOgolem),
                  ],
                },
                {
                  label: "kosztyMiesiac",
                  values: [fmt4(kosztMc), fmt4(kosztMcBez || kosztMc)],
                },
                {
                  label: "kosztDzienny",
                  values: [fmt4(kosztDzienny), fmt4(czynszInicjalnyNetto ? 0 : kosztDzienny)],
                },
              ]}
            />

            {/* MARZA NA KONTRAKCIE */}
            <LegacyMatrix
              title="MARZA NA KONTRAKCIE"
              titleColSpan={3}
              columns={["NETTO", "Marza symulowana (bez uwzglednienia CZ)"]}
              rows={[
                {
                  label: "marzaMC",
                  values: [fmt4(marzaMc), fmt4(marzaMc)],
                },
                {
                  label: "marzaNaKontrakcie",
                  values: [fmt4(marzaNaKontrakcie), fmt4(marzaNaKontrakcie)],
                },
                {
                  label: "marzaNaKontrakcieProcent",
                  values: [fmt4(marzaProcent), fmt4(marzaProcent)],
                },
                {
                  label: "przychod",
                  values: [fmt4(przychod), fmt4(przychod)],
                },
              ]}
            />

            {/* ROZKŁAD MARŻY (6 składowych, 9 kolumn) */}
            <LegacyMatrix
              columns={[
                "Rozkład marży",
                "Koszty łącznie",
                "Koszt MC",
                "Podział marży",
                "Podział marży ręczny",
                "Kwota marży",
                "Kwota marży podział ręczny",
                "Koszt+marża",
                "Koszt+marża podział ręczny",
              ]}
              rows={rozkladComponents.map((c) => {
                const rozklad = sumRozkladKoszty > 0 ? c.koszty / sumRozkladKoszty : 0;
                const kwotaMarzy = marzaMc * rozklad;
                return {
                  label: c.label,
                  values: [
                    fmt4(rozklad),
                    fmt4(c.koszty),
                    fmt4(c.baseMc),
                    fmt4(rozklad),
                    fmt4(rozklad),
                    fmt4(kwotaMarzy),
                    fmt4(kwotaMarzy),
                    fmt4(c.baseMc + kwotaMarzy),
                    fmt4(c.baseMc + kwotaMarzy),
                  ],
                };
              })}
            />

            {/* OFEROWANA STAWKA */}
            <LegacyTable
              title="OFEROWANA STAWKA"
              rows={[
                ["czynsz finansowy", fmt4(s11?.outputs?.czynsz_finansowy || 0)],
                ["czynszTechniczny", fmt4(s11?.outputs?.czynsz_techniczny || 0)],
                ["ubezpieczenie", fmt4(s8?.outputs?.insurance_base || 0)],
                ["samochód zastępczy", fmt4(s3?.outputs?.rc_base || 0)],
                ["serwis", fmt4(s4?.outputs?.service_base || 0)],
                [
                  "opony (łączny koszt opon na kontrakt)",
                  fmt4(months ? oponyTotal / months : 0),
                ],
                ["koszty dodatkowe", fmt4(s2?.outputs?.additional_costs_base || 0)],
              ]}
            />

            {/* BUDŻET MARKETINGOWY */}
            <LegacyTable
              title="BUDŻET MARKETINGOWY"
              rows={[
                ["korektaWRMaksBrutto", fmt4(s12?.outputs?.korekta_wr_maks || 0)],
              ]}
            />
          </div>
        ) : view === "pipeline" ? (
          <div className="max-w-5xl mx-auto space-y-3">
            {steps.map((step) => (
              <details
                key={step.step}
                className="border border-slate-200 rounded-lg p-3 bg-white open:bg-slate-50"
                open={step.step <= 3}
              >
                <summary className="cursor-pointer font-bold text-slate-800 text-sm flex items-center gap-2">
                  <span className="bg-indigo-100 text-indigo-700 text-xs px-2 py-0.5 rounded">
                    {step.step}
                  </span>
                  {step.name}
                </summary>
                <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div>
                    <h5 className="font-semibold mb-1 text-emerald-700">Outputs</h5>
                    <pre className="bg-emerald-50 p-2 rounded border border-emerald-200 overflow-x-auto max-h-64 overflow-y-auto">
                      {JSON.stringify(step.outputs, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <h5 className="font-semibold mb-1 text-slate-600">Inputs</h5>
                    <pre className="bg-slate-100 p-2 rounded border border-slate-200 overflow-x-auto max-h-64 overflow-y-auto">
                      {JSON.stringify(step.inputs, null, 2)}
                    </pre>
                  </div>
                </div>
                {step.trace && step.trace.length > 0 && (
                  <div className="mt-3">
                    <h5 className="font-semibold mb-1 text-amber-700 text-xs">
                      Ślad rewizyjny ({step.trace.length})
                    </h5>
                    <ol className="text-xs space-y-1 list-decimal list-inside">
                      {step.trace.map((t, i) => {
                        if (typeof t === "string") {
                          return (
                            <li key={i} className="font-mono text-slate-600">
                              {t}
                            </li>
                          );
                        }
                        return (
                          <li key={i} className="font-mono text-slate-600">
                            <span className="font-bold">{t.krok}</span>
                            {t.rownanie && (
                              <span className="text-slate-500"> · {t.rownanie}</span>
                            )}
                            {t.wynik !== null && t.wynik !== undefined && (
                              <span className="ml-2 text-blue-700">→ {fmt4(t.wynik)}</span>
                            )}
                          </li>
                        );
                      })}
                    </ol>
                  </div>
                )}
              </details>
            ))}
          </div>
        ) : (
          <pre className="text-[11px] font-mono bg-slate-900 text-slate-100 p-4 rounded-lg overflow-auto h-full">
            {jsonText}
          </pre>
        )}
      </div>
    </div>
  );
}

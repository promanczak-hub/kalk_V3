import { useState, useCallback, useRef, useMemo } from "react";
import { API_BASE_URL } from "../../../../config/env";
import type { MiniMatrixCell } from "../decision-center/decision-center.types";
import { findBestCell } from "../decision-center/decision-center.utils";
import { extractOptionsFromPaidOptions, parsePriceToNumber } from "./calculations.utils";
import type { MatrixFilters, MileageMode } from "../../../../CalculatorPanel/MatrixFilterToolbar";
import { apiClient } from "../../../../lib/apiClient";

export interface CellOverrides {
  pricing_margin_pct: number | null;
  klasa_opony_string: string;
  liczba_kompletow_opon: number | null;
  z_oponami: boolean;
  manual_wr_correction: number;
  pakiet_serwisowy: number;
  inne_koszty_serwisowania_netto: number;
  service_cost_type: "ASO" | "nonASO";
  replacement_car_enabled: boolean;
  custom_months: number | null;
  custom_km_per_year: number | null;
  tire_cost_correction_brutto: number | null;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Payload = Record<string, any>;

export interface TraceData {
  krok: string;
  rownanie: string;
  wynik: unknown;
}

interface UseVehicleCalculationsProps {
  kalkulacjaId: string;
  vehicleId: string;
  onBestPriceFound?: (price: number | null) => void;
  onSpecificPriceFound?: (price: number | null) => void;
}

export function useVehicleCalculations({
  kalkulacjaId,
  vehicleId,
  onBestPriceFound,
  onSpecificPriceFound,
}: UseVehicleCalculationsProps) {
  const [cells, setCells] = useState<MiniMatrixCell[]>([]);
  const [originalCells, setOriginalCells] = useState<MiniMatrixCell[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [cellOverrides, setCellOverrides] = useState<Record<number, CellOverrides>>({});
  const [modifiedCells, setModifiedCells] = useState<Set<number>>(new Set());
  
  const [recalculating, setRecalculating] = useState<number | null>(null);
  const [fetchingTraceCell, setFetchingTraceCell] = useState<number | null>(null);
  const [traceData, setTraceData] = useState<TraceData[] | null>(null);
  
  const [marginRecalculating, setMarginRecalculating] = useState(false);
  const [globalWrCorrection, setGlobalWrCorrection] = useState<number>(0);
  const [globalTireCorrection, setGlobalTireCorrection] = useState<number>(0);
  const [isGlobalRecalculating, setIsGlobalRecalculating] = useState(false);

  const [mileageMode, setMileageMode] = useState<MileageMode>("contract");
  const [filters, setFilters] = useState<MatrixFilters>({
    monthsRange: [12, 84],
    targetKmPerYear: null,
    globalMarginPct: null,
  });

  const [basePayload, setBasePayload] = useState<Payload | null>(null);
  
  const validatePayload = (payload: Payload): string | null => {
    if (!payload.base_price_net || payload.base_price_net <= 0) {
      return "Błąd: Brak ceny bazowej pojazdu (musi być > 0). Uzupełnij dane w Vertex Extractor lub Karcie Pojazdu.";
    }
    if (!payload.engine_name || !payload.engine_name.trim()) {
      return "Błąd: Brak rodzaju silnika (engine_name). Wymagane dla logiki stawkowej serwisu.";
    }
    if (!payload.samar_category || !payload.samar_category.trim()) {
      return "Błąd: Brak klasy SAMAR. Wymagane dla logiki Wartości Rezydualnej.";
    }
    return null;
  };

  const mileageReferenceMonths = useMemo(() => {
    const [from, to] = filters.monthsRange;
    if (from === to && from > 0) return from;
    return 48;
  }, [filters.monthsRange]);

  const kmPerMonthRef = useRef<number>(0);

  const buildDefaultOverrides = (payload: Payload): CellOverrides => ({
    pricing_margin_pct: payload.pricing_margin_pct ?? null,
    klasa_opony_string: payload.klasa_opony_string || "Medium",
    liczba_kompletow_opon: payload.liczba_kompletow_opon ?? null,
    z_oponami: payload.z_oponami !== false,
    manual_wr_correction: payload.manual_wr_correction || 0,
    pakiet_serwisowy: payload.pakiet_serwisowy || 0,
    inne_koszty_serwisowania_netto: payload.inne_koszty_serwisowania_netto || 0,
    service_cost_type: payload.service_cost_type || "ASO",
    replacement_car_enabled: payload.replacement_car_enabled !== false,
    custom_months: null,
    custom_km_per_year: null,
    tire_cost_correction_brutto: null,
  });

  const getOverrides = (months: number): CellOverrides => {
    if (cellOverrides[months]) return cellOverrides[months];
    if (basePayload) return buildDefaultOverrides(basePayload);
    return {
      pricing_margin_pct: null,
      klasa_opony_string: "Medium",
      liczba_kompletow_opon: null,
      z_oponami: true,
      manual_wr_correction: 0,
      pakiet_serwisowy: 0,
      inne_koszty_serwisowania_netto: 0,
      service_cost_type: "ASO",
      replacement_car_enabled: true,
      custom_months: null,
      custom_km_per_year: null,
      tire_cost_correction_brutto: null,
    };
  };

  const fetchMatrix = useCallback(async () => {
    if (!kalkulacjaId) {
      setError("Brak ID kalkulacji.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const kalkResp = await apiClient.fetch(`${API_BASE_URL}/api/kalkulacje/${kalkulacjaId}`);
      if (!kalkResp.ok) throw new Error(`Nie znaleziono kalkulacji ${kalkulacjaId}`);
      const kalkData = await kalkResp.json();
      const stanJson = kalkData.stan_json || {};
      const cardSummary = stanJson.card_summary || {};
      const financialParams = stanJson.financial_params || {};
      const toggles = stanJson.toggles || {};
      const mappedAi = stanJson.mapped_ai_data || {};
      const discount = stanJson.discount || {};
      const pricing = stanJson.pricing || {};

      const okresBazowy = mappedAi.usage_months || 48;
      const przebiegBazowy = mappedAi.total_km || 140000;
      kmPerMonthRef.current = przebiegBazowy / okresBazowy;

      // --- ROBUST PRICE DISCOVERY (SYNC WITH BACKEND READYNESS CHECK) ---
      const sd = stanJson.synthesis_data || {};
      const cs = sd.card_summary || {};
      const setup = sd.calculator_setup || {};
      const pp = cs.parsed_prices || {};
      const uf = sd.universal_features || {};
      const comp = sd.computed || {};

      const rawBasePrice = String(
        setup.catalog_base_price_net || 
        cardSummary.base_price || 
        cardSummary.total_price || 
        pp.base || 
        uf.cena_pojazdu || 
        comp.estimated_price || 
        "0"
      );
      
      const cleanBasePrice = parsePriceToNumber(rawBasePrice);
      const priceDomain = cardSummary._price_domain || cardSummary.price_domain || "unknown";
      const isBrutto = rawBasePrice.toLowerCase().includes("brutto") || priceDomain === "brutto";
      
      const basePriceNet = isBrutto ? parseFloat((cleanBasePrice / 1.23).toFixed(2)) : cleanBasePrice;
      const resolvedVehicleId = vehicleId || stanJson.vehicle_id || kalkData.vehicle_id;
      if (!resolvedVehicleId) {
        throw new Error("Brak vehicle_id w kalkulacji.");
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const persistedFactoryOptions = (stanJson.factory_options || []).map((o: any) => ({
        name: o.name || "Opcja",
        price_net: o.price_net || 0,
        price_gross: o.price_gross || Number(((o.price_net || 0) * 1.23).toFixed(2)),
        no_discount: Boolean(o.no_discount),
        include_in_wr: false,
      }));

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const persistedServiceOptions = (stanJson.service_options || []).map((o: any) => ({
        name: o.name || "Usluga",
        price_net: o.price_net || 0,
        price_gross: o.price_gross || Number(((o.price_net || 0) * 1.23).toFixed(2)),
        no_discount: false,
        include_in_wr: Boolean(o.include_in_wr),
      }));

      const fallbackFromPaid = extractOptionsFromPaidOptions(
        cardSummary.paid_options,
        String(cardSummary._price_domain || cardSummary.price_domain || "")
      );

      const normalizedFactoryOptions =
        persistedFactoryOptions.length > 0
          ? persistedFactoryOptions
          : fallbackFromPaid.factory;

      const normalizedServiceOptions =
        persistedServiceOptions.length > 0
          ? persistedServiceOptions
          : fallbackFromPaid.service;

      const payload: Payload = {
        calculation_id: kalkulacjaId,
        vehicle_id: resolvedVehicleId,
        base_price_net: basePriceNet,
        discount_pct: pricing.discount_pct ?? discount.active_discount_pct ?? 0,
        factory_options: normalizedFactoryOptions,
        service_options: normalizedServiceOptions,
        okres_bazowy: okresBazowy,
        przebieg_bazowy: przebiegBazowy,
        // Wysyłamy null gdy brak explicit value w stan_json — backend pobiera WIBOR/spread z control_center
        // (source of truth). Hardcoded fallbacki (5.0/2.0) były przyczyną rozbieżności ~81 PLN vs ReverseLookup.
        wibor_pct: financialParams.wibor_pct ?? null,
        margin_pct: financialParams.margin_pct ?? null,
        depreciation_pct: financialParams.depreciation_pct || null,
        initial_deposit_pct: financialParams.initial_deposit_pct || 0,
        replacement_car_enabled: toggles.replacement_car !== false,
        add_gsm_subscription: toggles.gps_required !== false,
        add_hook_installation: toggles.hook_installation === true,
        add_grid_dismantling: toggles.grid_dismantling === true,
        add_registration: toggles.add_registration !== false,
        add_sales_prep: toggles.add_sales_prep !== false,
        korekta_kosztu_przygotowania: Number(
          financialParams.sales_prep_correction
            ?? financialParams.korekta_kosztu_przygotowania
            ?? stanJson.korekta_kosztu_przygotowania
            ?? stanJson.KosztPrzygotowaniaDosprzedazyKorekta
            ?? 0
        ),
        z_oponami: (toggles.include_tires ?? toggles.z_oponami) !== false,
        klasa_opony_string: stanJson.tire_params?.tire_class || "Medium",
        srednica_felgi: stanJson.tire_params?.rim_diameter || (cardSummary.wheels ? parseInt(String(cardSummary.wheels).replace(/\D/g, "")) : 16) || 16,
        liczba_kompletow_opon: stanJson.tire_params?.tire_count_mode === "auto" ? null : (isNaN(parseFloat(stanJson.tire_params?.tire_count_mode)) ? null : parseFloat(stanJson.tire_params?.tire_count_mode)),
        korekta_kosztu_opon: stanJson.tire_params?.tire_cost_correction_enabled !== false,
        koszt_opon_korekta: (stanJson.tire_params?.tire_cost_correction_map as Record<string, number>) || {},
        service_cost_type: stanJson.service_cost_type || "ASO",
        include_servicing: toggles.include_servicing !== false,
        vehicle_vintage: stanJson.vehicle_vintage || "current",
        is_metalic: stanJson.is_metalic === true,
        paint_type_id: (
          (typeof stanJson.paint_type_id === "number" && stanJson.paint_type_id > 0)
            ? stanJson.paint_type_id
            : (typeof stanJson.paint_category_id === "number" && stanJson.paint_category_id > 0)
              ? stanJson.paint_category_id
              : null
        ),
        pricing_margin_pct: financialParams.pricing_margin_pct ?? null,
        manual_wr_correction: 0,
        pakiet_serwisowy: Number(stanJson.pakiet_serwisowy ?? 0),
        inne_koszty_serwisowania_netto: Number(
          financialParams.other_service_costs ?? stanJson.inne_koszty_serwisowania_netto ?? 0
        ),
        matrix_km_mode: mileageMode,
        matrix_contract_km_step: 10000,
        settings: { settings_version_id: null, overrides: null },
        power_kw: Number(stanJson.power_kw ?? cardSummary.power_kw ?? (cardSummary.power_hp ? Number(cardSummary.power_hp) * 0.73549875 : 0)),
        paint_type_name: stanJson.mapped_ai_data?.color ?? stanJson.typ_lakieru ?? stanJson.paint_type_name ?? cardSummary.color ?? "",
        body_type_name: stanJson.mapped_ai_data?.body_type ?? stanJson.body_type_name ?? cardSummary.body_style ?? cardSummary.body_type ?? "",
        zabudowa_type_id: stanJson.zabudowa_type_id ?? ((typeof cardSummary.zabudowa_type_id === "number") ? cardSummary.zabudowa_type_id : null),
        samar_category: stanJson.mapped_ai_data?.samar_category 
          ?? stanJson.samar_category 
          ?? cardSummary.samar_category 
          ?? cs.samar_category 
          ?? "",
        engine_name: stanJson.mapped_ai_data?.fuel 
          ?? stanJson.engine_category 
          ?? cardSummary.engine_category 
          ?? cardSummary.powertrain 
          ?? cs.fuel_type 
          ?? uf.rodzaj_paliwa 
          ?? "",
      };

      setBasePayload(payload);

      const validationError = validatePayload(payload);
      if (validationError) {
        setError(validationError);
        setLoading(false);
        return;
      }

      const matrixResp = await apiClient.fetch(`${API_BASE_URL}/api/calculate-matrix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!matrixResp.ok) throw new Error(`Błąd kalkulacji: ${await matrixResp.text()}`);
      
      const matrixData = await matrixResp.json();
      const newCells = matrixData.cells || [];
      
      setCells(newCells);
      setOriginalCells(newCells);
      setModifiedCells(new Set());
      setCellOverrides({});
      setGlobalWrCorrection(0);

      if (onBestPriceFound) {
        const best = findBestCell(newCells);
        onBestPriceFound(best ? best.LacznaStawka : null);
      }

      if (onSpecificPriceFound) {
        const specificCell = newCells.find((c: MiniMatrixCell) => c.Okres === 48 && (c.PrzebiegKontrakt ?? ((c.Okres / 12) * c.Przebieg)) === 140000);
        onSpecificPriceFound(specificCell ? specificCell.LacznaStawka : null);
      }

      setFilters(prev => ({
        ...prev,
        globalMarginPct: payload.pricing_margin_pct ?? null,
      }));
    } catch (err) {
      console.error("Matrix fetch error:", err);
      setError(err instanceof Error ? err.message : "Nieznany błąd");
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kalkulacjaId, vehicleId, mileageMode]);

  const recalculateSingleCell = useCallback(async (months: number) => {
    if (!basePayload) return;
    const ov = cellOverrides[months];
    if (!ov) return;

    setRecalculating(months);
    try {
      const effectiveMonths = ov.custom_months ?? months;
      const effectiveKmYear = ov.custom_km_per_year;
      const targetKm = effectiveKmYear != null 
        ? Math.round((effectiveKmYear / 12) * effectiveMonths) 
        : Math.round(kmPerMonthRef.current * effectiveMonths);

      const modifiedPayload: Payload = {
        ...basePayload,
        okres_bazowy: effectiveMonths,
        przebieg_bazowy: targetKm,
        pricing_margin_pct: ov.pricing_margin_pct,
        klasa_opony_string: ov.klasa_opony_string,
        liczba_kompletow_opon: ov.liczba_kompletow_opon,
        z_oponami: ov.z_oponami,
        manual_wr_correction: ov.manual_wr_correction,
        pakiet_serwisowy: ov.pakiet_serwisowy,
        inne_koszty_serwisowania_netto: ov.inne_koszty_serwisowania_netto,
        service_cost_type: ov.service_cost_type,
        replacement_car_enabled: ov.replacement_car_enabled,
      };

      if (ov.tire_cost_correction_brutto !== null && ov.tire_cost_correction_brutto !== undefined) {
        modifiedPayload.koszt_opon_korekta = {
          ...(basePayload.koszt_opon_korekta || {}),
          [`${effectiveMonths}_${targetKm}`]: ov.tire_cost_correction_brutto
        };
        modifiedPayload.korekta_kosztu_opon = true;
      }

      const validationError = validatePayload(modifiedPayload);
      if (validationError) {
        alert(validationError);
        setRecalculating(null);
        return;
      }

      const resp = await apiClient.fetch(`${API_BASE_URL}/api/calculate-matrix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(modifiedPayload),
      });

      if (!resp.ok) throw new Error("Błąd przeliczania komórki");
      const data = await resp.json();
      const newCells: MiniMatrixCell[] = data.cells || [];

      const foundMonths = ov.custom_months ?? months;
      const targetCell = newCells.find(c => c.Okres === foundMonths);
      if (targetCell) {
        setCells(prev => prev.map(c => c.Okres === months ? targetCell : c));
        setModifiedCells(prev => new Set([...prev, months]));
      }
    } catch (err) {
      console.error("Recalculation error:", err);
    } finally {
      setRecalculating(null);
    }
  }, [cellOverrides, basePayload]);

  const fetchTraceSingleCell = useCallback(async (months: number, kmYearOverride?: number) => {
    if (!basePayload) return;
    const ov = cellOverrides[months] || buildDefaultOverrides(basePayload);
    
    setFetchingTraceCell(months);
    try {
      const effectiveMonths = ov.custom_months ?? months;
      const effectiveKmYear = kmYearOverride ?? ov.custom_km_per_year;
      const targetKm = effectiveKmYear != null 
        ? Math.round((effectiveKmYear / 12) * effectiveMonths) 
        : Math.round(kmPerMonthRef.current * effectiveMonths);

      const modifiedPayload: Payload = {
        ...basePayload,
        okres_bazowy: effectiveMonths,
        przebieg_bazowy: targetKm,
        pricing_margin_pct: ov.pricing_margin_pct,
        klasa_opony_string: ov.klasa_opony_string,
        liczba_kompletow_opon: ov.liczba_kompletow_opon,
        z_oponami: ov.z_oponami,
        manual_wr_correction: ov.manual_wr_correction,
        pakiet_serwisowy: ov.pakiet_serwisowy,
        inne_koszty_serwisowania_netto: ov.inne_koszty_serwisowania_netto,
        service_cost_type: ov.service_cost_type,
        replacement_car_enabled: ov.replacement_car_enabled,
      };

      if (ov.tire_cost_correction_brutto !== null && ov.tire_cost_correction_brutto !== undefined) {
        modifiedPayload.koszt_opon_korekta = {
          ...(basePayload.koszt_opon_korekta || {}),
          [`${effectiveMonths}_${targetKm}`]: ov.tire_cost_correction_brutto
        };
        modifiedPayload.korekta_kosztu_opon = true;
      }

      const resp = await apiClient.fetch(`${API_BASE_URL}/api/calculate-trace`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(modifiedPayload),
      });

      if (!resp.ok) throw new Error("Błąd pobierania śladu");
      const data = await resp.json();
      setTraceData(data.calculation_trace || []);
    } catch (err) {
      console.error("Trace error:", err);
      alert("Błąd pobierania śladu: " + err);
    } finally {
      setFetchingTraceCell(null);
    }
  }, [cellOverrides, basePayload]);

  const resetCell = (months: number) => {
    const original = originalCells.find(c => c.Okres === months);
    if (original) {
      setCells(prev => prev.map(c => c.Okres === months ? original : c));
    }
    setCellOverrides(prev => {
      const next = { ...prev };
      delete next[months];
      return next;
    });
    setModifiedCells(prev => {
      const next = new Set(prev);
      next.delete(months);
      return next;
    });
  };

  const handleOverridesChange = (months: number, overrides: Partial<CellOverrides>) => {
    setCellOverrides(prev => {
      const current = prev[months] || buildDefaultOverrides(basePayload || {});
      return { ...prev, [months]: { ...current, ...overrides } as CellOverrides };
    });
  };

  const filteredCells = useMemo(() => {
    return cells.filter((c) => {
      if (c.Okres < filters.monthsRange[0] || c.Okres > filters.monthsRange[1]) return false;
      
      const isBaseCell = basePayload && c.Okres === basePayload.okres_bazowy && (c.PrzebiegKontrakt ?? Math.round((c.Okres / 12) * c.Przebieg)) === basePayload.przebieg_bazowy;

      if (filters.targetKmPerYear === null) {
        // Gdy nie ma precyzyjnego filtru, pokazuj kafelki tylko co 5000km (np. 10k, 15k, 20k) dla danego trybu
        const kmValue = mileageMode === "contract" 
          ? (c.PrzebiegKontrakt ?? Math.round((c.Okres / 12) * c.Przebieg))
          : c.Przebieg;
          
        if (kmValue % 5000 !== 0 && !isBaseCell) {
          return false;
        }
        return true;
      }

      if (mileageMode === "contract") {
        const targetContractKm = (filters.targetKmPerYear / 12) * mileageReferenceMonths;
        const lo = targetContractKm * 0.95;
        const hi = targetContractKm * 1.05;
        const contractKm = c.PrzebiegKontrakt ?? (c.Przebieg / 12) * c.Okres;
        return contractKm >= lo && contractKm <= hi;
      }

      const lo = filters.targetKmPerYear * 0.95;
      const hi = filters.targetKmPerYear * 1.05;
      return c.Przebieg >= lo && c.Przebieg <= hi;
    });
  }, [cells, filters.monthsRange, filters.targetKmPerYear, mileageMode, mileageReferenceMonths, basePayload]);

  const recalculateWithMargin = useCallback(async (marginPct: number) => {
    if (!basePayload) return;
    setMarginRecalculating(true);
    try {
      const modifiedPayload = {
        ...basePayload,
        pricing_margin_pct: marginPct,
      };

      const validationError = validatePayload(modifiedPayload);
      if (validationError) {
        setError(validationError);
        setMarginRecalculating(false);
        return;
      }

      const resp = await apiClient.fetch(`${API_BASE_URL}/api/calculate-matrix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(modifiedPayload),
      });
      if (!resp.ok) throw new Error("Błąd przeliczania matrycy");
      const data = await resp.json();
      const newCells = data.cells || [];
      setCells(newCells);
      setOriginalCells(newCells);
      setModifiedCells(new Set());
      setCellOverrides({});
      setFilters(prev => ({ ...prev, globalMarginPct: marginPct }));
    } catch (err) {
      console.error("Margin recalculation error:", err);
    } finally {
      setMarginRecalculating(false);
    }
  }, [basePayload]);

  const handleExactRecalculate = useCallback(async (months: number, kmPerYear: number, marginPct: number, targetPrice?: number) => {
    if (!basePayload) return;
    setMarginRecalculating(true);
    try {
      const targetKm = Math.round((kmPerYear / 12) * months);
      const modifiedPayload: Payload = {
        ...basePayload,
        okres_bazowy: months,
        przebieg_bazowy: targetKm,
        pricing_margin_pct: marginPct,
      };
      
      if (targetPrice !== undefined && targetPrice > 0) {
        modifiedPayload.pricing_exact_price = targetPrice;
      }

      const resp = await apiClient.fetch(`${API_BASE_URL}/api/calculate-matrix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(modifiedPayload),
      });

      if (!resp.ok) throw new Error("Błąd przeliczania wariantu precyzyjnego");
      const data = await resp.json();
      const newCells = data.cells || [];
      
      setCells(newCells);
      setOriginalCells(newCells);
      setModifiedCells(new Set());
      setCellOverrides({});

      setFilters(prev => ({
        ...prev,
        monthsRange: [
          Math.min(prev.monthsRange[0], months),
          Math.max(prev.monthsRange[1], months)
        ],
        targetKmPerYear: null,
        globalMarginPct: marginPct,
      }));
    } catch (err) {
      console.error("Exact variant recalculation error:", err);
    } finally {
      setMarginRecalculating(false);
    }
  }, [basePayload]);

  const handleGlobalRecalculate = useCallback(async () => {
    if (!basePayload) return;
    setIsGlobalRecalculating(true);
    try {
      const modifiedPayload = {
        ...basePayload,
        manual_wr_correction: globalWrCorrection,
        koszt_opon_korekta: globalTireCorrection,
        korekta_kosztu_opon: globalTireCorrection !== 0,
      };
      setBasePayload(modifiedPayload);
      const resp = await apiClient.fetch(`${API_BASE_URL}/api/calculate-matrix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(modifiedPayload),
      });

      if (!resp.ok) throw new Error("Błąd przeliczania matrycy z korektami");
      const data = await resp.json();
      const newCells = data.cells || [];
      
      setCells(newCells);
      setOriginalCells(newCells);
      setModifiedCells(new Set());
      setCellOverrides({});
    } catch (err) {
      console.error("Global recalculation error:", err);
    } finally {
      setIsGlobalRecalculating(false);
    }
  }, [globalWrCorrection, globalTireCorrection, basePayload]);

  return {
    cells,
    filteredCells,
    loading,
    error,
    traceData,
    setTraceData,
    recalculating,
    fetchingTraceCell,
    marginRecalculating,
    basePayload,
    filters,
    setFilters,
    mileageMode,
    setMileageMode,
    mileageReferenceMonths,
    isGlobalRecalculating,
    globalWrCorrection,
    setGlobalWrCorrection,
    globalTireCorrection,
    setGlobalTireCorrection,
    modifiedCells,
    getOverrides,
    fetchMatrix,
    handleOverridesChange,
    recalculateSingleCell,
    resetCell,
    fetchTraceSingleCell,
    handleExactRecalculate,
    handleGlobalRecalculate,
    recalculateWithMargin
  };
}

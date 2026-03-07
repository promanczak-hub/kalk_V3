import { useState, useEffect } from "react";
import type { FleetVehicleView } from "../types";

interface PipelineDebuggerProps {
  vehicle: FleetVehicleView;
  onClose: () => void;
}

interface DebugStep {
  step: number;
  name: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  inputs: Record<string, any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  outputs: Record<string, any>;
  metadata?: Record<string, {source: string, formula: string}>;
}

interface DebuggerState {
  status: "idle" | "loading" | "success" | "error";
  steps: DebugStep[];
  error?: string;
}

interface AiChatState {
  query: string;
  response: string;
  isLoading: boolean;
  error?: string;
}

// --- V1 Diagnostyka helpers ---
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const fmt = (v: any): string => {
  if (v === null || v === undefined) return "-";
  const n = Number(v);
  return isNaN(n) ? String(v) : n.toFixed(4);
};

const V1_SECTION_NAMES: Record<number, string> = {
  1: "OPONY",
  2: "KOSZTY DODATKOWE",
  3: "SAMOCHÓD ZASTĘPCZY",
  4: "SERWIS",
  5: "CENA ZAKUPU (wartości netto)",
  6: "UTRATA WARTOŚCI (NOWA)",
  7: "AMORTYZACJA",
  8: "UBEZPIECZENIE",
  9: "FINANSOWE",
  10: "KOSZT DZIENNY",
  11: "MARŻA NA KONTRAKCIE / OFEROWANA STAWKA",
  12: "BUDŻET MARKETINGOWY",
};

function V1Section({ title, rows }: { title: string; rows: [string, string, boolean?][] }) {
  return (
    <table className="w-full border-collapse border border-slate-400 text-[13px]">
      <thead>
        <tr>
          <td colSpan={2} className="bg-slate-100 border border-slate-400 px-2 py-1 font-bold text-slate-800 text-[13px]">
            {title}
          </td>
        </tr>
      </thead>
      <tbody>
        {rows.map(([label, value, bold], i) => (
          <tr key={i}>
            <td className={`border border-slate-300 px-2 py-0.5 text-slate-700 whitespace-nowrap ${bold ? "font-bold" : ""}`}>
              {label}
            </td>
            <td className={`border border-slate-300 px-2 py-0.5 text-right tabular-nums ${bold ? "font-bold text-slate-900" : "text-slate-700"}`}>
              {value}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function PipelineDebugger({ vehicle, onClose }: PipelineDebuggerProps) {
  const [activeStep, setActiveStep] = useState<number>(1);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [overrides, setOverrides] = useState<Record<string, any>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [aiChats, setAiChats] = useState<Record<number, AiChatState>>({});
  const [months, setMonths] = useState<number>(48);
  const [viewMode, setViewMode] = useState<"pipeline" | "diagnostyka">("pipeline");
  
  const [state, setState] = useState<DebuggerState>({
    status: "idle",
    steps: []
  });

  const fetchPipeline = async () => {
    setState((s) => ({ ...s, status: "loading", error: undefined }));
    try {
      // Extract pricing from synthesis_data (primary source)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const sd = (vehicle.synthesis_data as Record<string, any>) || {};
      const cs = sd?.card_summary || {};
      const calcSetup = sd?.calculator_setup || {};
      const finParams = calcSetup?.financial_params || {};
      const tireParams = calcSetup?.tire_params || {};
      const toggles = calcSetup?.toggles || {};
      const discountBlock = calcSetup?.discount || {};

      // ── Base price net: parse "154 250 zł brutto" → netto ──
      let basePriceNet = 0;
      const basePriceStr = cs.base_price || vehicle.base_price || "";
      if (basePriceStr) {
        const numMatch = String(basePriceStr).replace(/\s/g, "").match(/([\d,.]+)/);
        if (numMatch) {
          const parsed = parseFloat(numMatch[1].replace(",", "."));
          const isBrutto = String(basePriceStr).toLowerCase().includes("brutto");
          basePriceNet = isBrutto ? Math.round((parsed / 1.23) * 100) / 100 : parsed;
        }
      }

      // ── Discount: from calculator_setup.discount or suggested ──
      const discountPct = Number(
        discountBlock.active_discount_pct
        || cs.suggested_discount_pct
        || vehicle.discount_pct
        || 0
      );

      // ── Factory options: parse paid_options from card_summary ──
      // Format in DB: [{name, price: "2650 zł brutto", category: "Fabryczna"}]
      // Backend VehicleOptions requires: {name, price_net, price_gross, no_discount}
      const paidOptions = cs.paid_options || [];
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const factoryOptions = paidOptions.map((opt: any) => {
        let priceNet = 0;
        if (opt.price) {
          const priceMatch = String(opt.price).replace(/\s/g, "").match(/([\d,.]+)/);
          if (priceMatch) {
            const rawPrice = parseFloat(priceMatch[1].replace(",", "."));
            const optIsBrutto = String(opt.price).toLowerCase().includes("brutto");
            priceNet = optIsBrutto ? Math.round((rawPrice / 1.23) * 100) / 100 : rawPrice;
          }
        }
        return {
          name: opt.name || "",
          price_net: priceNet,
          price_gross: Math.round(priceNet * 1.23 * 100) / 100,
          no_discount: opt.no_discount ?? false,
        };
      });

      // Service options (empty for now — rarely present in card_summary)
      const serviceOptions = cs.service_options || vehicle.service_options || [];

      // ── Reconstruct payload from synthesis_data ──
      const payload = {
        base_price_net: basePriceNet,
        discount_pct: discountPct,
        factory_options: factoryOptions,
        service_options: serviceOptions,
        wibor_pct: finParams.wibor_pct ?? vehicle.wibor_pct ?? 5.85,
        margin_pct: finParams.margin_pct ?? vehicle.margin_pct ?? 2.0,
        pricing_margin_pct: finParams.pricing_margin_pct ?? vehicle.pricing_margin_pct ?? 15.0,
        depreciation_pct: finParams.depreciation_pct ?? vehicle.depreciation_pct,
        initial_deposit_pct: finParams.initial_deposit_pct ?? vehicle.initial_deposit_pct ?? 0.0,
        z_oponami: vehicle.z_oponami ?? true,
        klasa_opony_string: tireParams.tire_class || vehicle.klasa_opony_string || "Medium",
        srednica_felgi: tireParams.rim_diameter || (vehicle.wheels && vehicle.wheels !== "Brak" ? parseInt(vehicle.wheels) : 18),
        korekta_kosztu_opon: tireParams.tire_cost_correction_enabled ?? vehicle.korekta_kosztu_opon ?? false,
        koszt_opon_korekta: tireParams.tire_cost_correction ?? vehicle.koszt_opon_korekta ?? 0.0,
        service_cost_type: calcSetup.service_cost_type || vehicle.service_cost_type || "ASO",
        okres_bazowy: vehicle.okres_bazowy || 48,
        przebieg_bazowy: vehicle.przebieg_bazowy || 140000,
        replacement_car_enabled: toggles.replacement_car ?? vehicle.replacement_car_enabled ?? true,
        pakiet_serwisowy: vehicle.pakiet_serwisowy || 0.0,
        inne_koszty_serwisowania_netto: finParams.other_service_costs ?? vehicle.inne_koszty_serwisowania_netto ?? 0.0,
        is_metalic: calcSetup.is_metalic ?? cs.is_metalic_paint ?? true,
        vehicle_vintage: calcSetup.vehicle_vintage || "current",

        // Debugger specific fields
        overrides,
        months
      };

      const res = await fetch(`http://localhost:8000/api/kalkulacje/debug-pipeline/${vehicle.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`Błąd API: ${res.status} - ${txt}`);
      }
      
      const data = await res.json();
      setState({ status: "success", steps: data.steps });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (e: any) {
      setState({ status: "error", steps: [], error: e.message });
    }
  };

  useEffect(() => {
    if (vehicle.id) {
      fetchPipeline();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicle.id]);

  const handleApplyOverrides = () => {
    fetchPipeline();
  };

  const handleOverrideChange = (stepKey: string, value: string) => {
    const numValue = parseFloat(value);
    setOverrides(prev => {
      const copy = { ...prev };
      if (isNaN(numValue) && value === "") {
        delete copy[stepKey];
      } else {
        copy[stepKey] = isNaN(numValue) ? value : numValue;
      }
      return copy;
    });
  };

  const handleNoteChange = (outputKey: string, value: string) => {
    setNotes(prev => ({
      ...prev,
      [outputKey]: value
    }));
  };

  const handleAiQueryChange = (step: number, value: string) => {
    setAiChats(prev => ({
      ...prev,
      [step]: { ...(prev[step] || { response: "", isLoading: false }), query: value }
    }));
  };

  const askAi = async (step: number) => {
    const chat = aiChats[step];
    if (!chat || !chat.query?.trim()) return;

    const stepData = state.steps.find(s => s.step === step);
    if (!stepData) return;

    setAiChats(prev => ({
      ...prev,
      [step]: { ...prev[step], isLoading: true, error: undefined, response: "" }
    }));

    try {
      const payload = {
        step_name: stepData.name,
        inputs: stepData.inputs,
        outputs: stepData.outputs,
        metadata: stepData.metadata,
        query: chat.query
      };

      const res = await fetch(`http://localhost:8000/api/kalkulacje/debug-pipeline/${vehicle.id}/ask-ai`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`Błąd API: ${res.status} - ${txt}`);
      }
      
      const data = await res.json();
      setAiChats(prev => ({
        ...prev,
        [step]: { ...prev[step], isLoading: false, response: data.answer }
      }));
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (e: any) {
      setAiChats(prev => ({
        ...prev,
        [step]: { ...prev[step], isLoading: false, error: e.message }
      }));
    }
  };

  const currentStepData = state.steps.find((s) => s.step === activeStep);
  const currentAiChat = aiChats[activeStep] || { query: "", response: "", isLoading: false };

  return (
    <div className="fixed inset-0 z-[100] bg-slate-900/50 flex flex-col pt-10 px-10 pb-10">
      <div className="bg-white rounded-xl shadow-2xl flex-1 flex flex-col overflow-hidden max-w-7xl w-full mx-auto relative border border-slate-200">
        
        {/* HEADER */}
        <div className="h-16 border-b border-slate-200 flex items-center justify-between px-6 bg-slate-50 shrink-0">
          <div className="flex items-center space-x-4">
            <h2 className="text-lg font-bold text-slate-800">Pipeline Debugger</h2>
            {/* View mode toggle */}
            <div className="flex bg-slate-200 rounded-lg p-0.5">
              <button
                onClick={() => setViewMode("pipeline")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  viewMode === "pipeline" ? "bg-white text-indigo-700 shadow-sm" : "text-slate-500 hover:text-slate-700"
                }`}
              >Pipeline</button>
              <button
                onClick={() => setViewMode("diagnostyka")}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  viewMode === "diagnostyka" ? "bg-white text-amber-700 shadow-sm" : "text-slate-500 hover:text-slate-700"
                }`}
              >Diagnostyka V1</button>
            </div>
            <span className="text-sm text-slate-500 font-mono">{vehicle.id}</span>
          </div>
          <div className="flex items-center space-x-3">
             <div className="flex items-center space-x-2 text-sm">
                <span className="text-slate-500">Miesiące (Months):</span>
                <input 
                  type="number" 
                  value={months} 
                  onChange={e => setMonths(parseInt(e.target.value) || 48)}
                  className="w-16 border border-slate-300 rounded px-2 py-1 text-center"
                />
             </div>
             <button 
               onClick={handleApplyOverrides}
               disabled={state.status === "loading"}
               className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-1.5 rounded-md text-sm font-medium transition-colors disabled:opacity-75 disabled:cursor-not-allowed flex items-center justify-center min-w-[180px]"
             >
               {state.status === "loading" ? (
                 <>
                   <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                     <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                     <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                   </svg>
                   Przeliczanie...
                 </>
               ) : (
                 "Przelicz z Nadpisaniami"
               )}
             </button>
             <button 
               onClick={onClose}
               className="p-2 hover:bg-slate-200 rounded-full text-slate-400 hover:text-slate-600 transition-colors"
             >
               <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
               </svg>
             </button>
          </div>
        </div>

        {/* CONTENT */}
        <div className="flex-1 flex overflow-hidden">

          {viewMode === "diagnostyka" ? (
            /* ============ DIAGNOSTYKA V1 — FLAT REPORT ============ */
            <div className="flex-1 bg-white overflow-y-auto p-6">
              {state.status === "loading" && state.steps.length === 0 ? (
                <div className="p-8 text-center text-slate-400">Ładowanie diagnostyki...</div>
              ) : state.status === "error" ? (
                <div className="p-4 bg-red-50 text-red-600 border border-red-200 rounded-md">
                  <strong>Błąd wyliczeń:</strong> {state.error}
                </div>
              ) : (
                <div className="max-w-3xl mx-auto space-y-6 font-mono text-[13px]">
                  <div className="text-center text-xs text-slate-400 mb-2 font-sans">Diagnostyka przeliczenie — {months} msc</div>

                  {/* GŁÓWNE PARAMETRY */}
                  <V1Section title={`GŁÓWNE PARAMETRY (${vehicle.id?.slice(0,8)})`} rows={[
                    ["Marka", vehicle.brand || "-"],
                    ["Model", vehicle.model || "-"],
                    ["OkresUżytkowania", String(months)],
                    ["Przebieg", String(Math.round((vehicle.przebieg_bazowy || 140000) / (vehicle.okres_bazowy || 48) * months))],
                    ["CenaCennikowa", fmt(vehicle.base_price_net)],
                    ["Rabat %", fmt(vehicle.discount_pct)],
                    ["Rabat kwotowo", fmt((vehicle.base_price_net || 0) * (vehicle.discount_pct || 0) / 100)],
                    ["Opcje fabryczne (suma)", fmt((vehicle.factory_options || []).reduce((s: number, o: {price_net?: number}) => s + (o.price_net || 0), 0))],
                    ["Marża", fmt(vehicle.pricing_margin_pct)],
                    ["ZOponami", vehicle.z_oponami ? "✓" : ""],
                    ["SamochodZastępczy", vehicle.replacement_car_enabled ? "✓" : ""],
                    ["WIBOR %", fmt(vehicle.wibor_pct)],
                    ["Marża Finansowa %", fmt(vehicle.margin_pct)],
                  ]} />

                  {/* WYNIK NETTO — summary */}
                  {(() => {
                    const findStep = (n: number) => state.steps.find(s => s.step === n);
                    const s1 = findStep(1);
                    const s2 = findStep(2);
                    const s3 = findStep(3);
                    const s4 = findStep(4);
                    const s5 = findStep(5);
                    const s6 = findStep(6);
                    const s8 = findStep(8);
                    const s9 = findStep(9);
                    const s10 = findStep(10);
                    const s11 = findStep(11);
                    const s12 = findStep(12);
                    return (
                      <V1Section title="WYNIK NETTO" rows={[
                        ["Cena zakupu", fmt(s5?.outputs?.capex_for_financing), true],
                        ["Serwis", fmt(s4?.outputs?.service_total)],
                        ["Opony", fmt(s1?.outputs?.tires_total)],
                        ["Ubezpieczenie", fmt(s8?.outputs?.insurance_total)],
                        ["Koszty dodatkowe", fmt(s2?.outputs?.additional_costs_total)],
                        ["Samochód zastępczy", fmt(s3?.outputs?.rc_total)],
                        ["Finansowe", fmt(s9?.outputs?.koszt_finansowy)],
                        ["Utrata wartości", fmt(s6?.outputs?.utrata_z_czynszem)],
                        ["Koszt dzienny", fmt(s10?.outputs?.koszt_dzienny)],
                        ["Marża na kontrakcie", fmt(s11?.outputs?.marza_na_kontrakcie)],
                        ["Oferowana stawka", fmt(s11?.outputs?.oferowana_stawka), true],
                        ["Budżet marketingowy korekta", fmt(s12?.outputs?.korekta_wr_maks)],
                      ]} />
                    );
                  })()}

                  {/* Per-step sections */}
                  {state.steps.map((step) => (
                    <V1Section
                      key={step.step}
                      title={V1_SECTION_NAMES[step.step] || step.name.toUpperCase()}
                      rows={Object.entries(step.outputs).map(([k, v]) => [
                        k,
                        typeof v === "number" ? v.toFixed(4) : String(v ?? ""),
                        // Bold the last/main output per section
                        k === Object.keys(step.outputs)[Object.keys(step.outputs).length - 1],
                      ])}
                    />
                  ))}

                  {/* Inputs detail sections */}
                  {state.steps.map((step) => {
                    const inputEntries = Object.entries(step.inputs).filter(
                      ([, v]) => typeof v !== "object" || v === null
                    );
                    if (inputEntries.length === 0) return null;
                    return (
                      <details key={`inp-${step.step}`} className="group">
                        <summary className="cursor-pointer text-[11px] text-slate-400 hover:text-slate-600">
                          Szczegóły wejść: {step.name}
                        </summary>
                        <V1Section
                          title={`WEJŚCIA — ${step.name}`}
                          rows={inputEntries.map(([k, v]) => [k, String(v ?? "")])}
                        />
                      </details>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            /* ============ PIPELINE MODE (original) ============ */
            <>
          {/* SIDEBAR - STEPS */}
          <div className="w-64 bg-slate-50 border-r border-slate-200 overflow-y-auto shrink-0 py-4">
             {state.status === "loading" && state.steps.length === 0 ? (
               <div className="p-4 text-center text-slate-400 text-sm">Ładowanie...</div>
             ) : (
                <div className="space-y-1 px-3">
                  {state.steps.map((s) => (
                    <button
                      key={s.step}
                      onClick={() => setActiveStep(s.step)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors flex items-center ${
                        activeStep === s.step 
                          ? "bg-indigo-100 text-indigo-700 font-semibold" 
                          : "text-slate-600 hover:bg-slate-200"
                      }`}
                    >
                      <span className="w-6 text-center shrink-0 opacity-50 mr-2">{s.step}.</span>
                      <span className="truncate">{s.name}</span>
                    </button>
                  ))}
                </div>
             )}
          </div>

          {/* MAIN AREA */}
          <div className="flex-1 bg-white overflow-y-auto p-6">
            {state.status === "error" ? (
              <div className="p-4 bg-red-50 text-red-600 border border-red-200 rounded-md">
                <strong>Błąd wyliczeń:</strong> {state.error}
              </div>
            ) : currentStepData ? (
              <div className="max-w-4xl">
                <h3 className="text-xl font-black text-slate-800 mb-6 flex items-center">
                  <span className="bg-slate-800 text-white w-8 h-8 flex items-center justify-center rounded-lg mr-3 text-sm">
                    {currentStepData.step}
                  </span>
                  {currentStepData.name}
                </h3>
                
                <div className="grid grid-cols-2 gap-8">
                  {/* LEFT COLUMN: Values */}
                  <div className="space-y-6">
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 border-b pb-1">Wejścia (Inputs)</h4>
                      <pre className="bg-slate-50 p-4 rounded-lg border border-slate-200 text-xs font-mono text-slate-700 overflow-x-auto">
                        {JSON.stringify(currentStepData.inputs, null, 2)}
                      </pre>
                    </div>
                    
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 border-b pb-1">Wyjścia (Outputs)</h4>
                      <div className="bg-emerald-50 p-4 rounded-lg border border-emerald-100">
                        <table className="w-full text-sm">
                          <tbody>
                            {Object.entries(currentStepData.outputs).map(([key, val]) => {
                               const meta = currentStepData.metadata?.[key];
                               return (
                                 <tr key={key} className="border-b border-emerald-100/50 last:border-0">
                                   <td className="py-3 pr-4">
                                     <div className="flex justify-between items-center mb-1">
                                       <span className="text-emerald-800/90 font-mono text-sm font-semibold">{key}</span>
                                       <span className="text-right font-bold text-emerald-900 text-sm">
                                         {typeof val === 'number' ? val.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : String(val)}
                                       </span>
                                     </div>
                                     {meta && (
                                       <div className="mt-2 pl-2 border-l-2 border-emerald-200">
                                          <div className="text-[10px] text-emerald-700/80 mb-0.5"><span className="font-semibold">Źródło:</span> {meta.source}</div>
                                          <div className="text-[10px] text-emerald-700/80"><span className="font-semibold">Wzór:</span> {meta.formula}</div>
                                       </div>
                                     )}
                                     <div className="mt-2">
                                        <textarea
                                          className="w-full text-xs p-2 rounded border border-emerald-200 bg-white/50 focus:bg-white focus:ring-1 focus:ring-emerald-400 placeholder-emerald-400/60"
                                          placeholder="Twoje uwagi do tego wyliczenia..."
                                          rows={2}
                                          value={notes[`${currentStepData.step}_${key}`] || ""}
                                          onChange={(e) => handleNoteChange(`${currentStepData.step}_${key}`, e.target.value)}
                                        />
                                     </div>
                                   </td>
                                 </tr>
                               );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>

                  {/* RIGHT COLUMN: Overrides */}
                  <div>
                     <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-400 mb-3 border-b border-indigo-100 pb-1">Nadpisania (Overrides)</h4>
                     <p className="text-xs text-slate-500 mb-4 leading-relaxed">
                       Wprowadź wartości poniżej, aby nadpisać wyjścia z tego etapu przed przekazaniem ich do następnych kroków kaskady.
                     </p>
                     
                     <div className="space-y-4 bg-indigo-50/50 p-4 rounded-lg border border-indigo-100">
                        {Object.entries(currentStepData.outputs).map(([key, val]) => {
                          // Convention: overrides keys are e.g., step_6_wr
                          // We map specific output keys to override keys. Since the backend expects specific override keys
                          // It's best we generate likely override keys or let the user type them.
                          
                          // Simplified heuristic for demo:
                          let overrideKey = `step_${currentStepData.step}_${key}`;
                          
                          // Map back to known override names from the backend implementation:
                          // e.g. step_6_wr for 'vr_samar'
                          if (currentStepData.step === 6 && key === "vr_samar") overrideKey = "step_6_wr";
                          if (currentStepData.step === 6 && key === "utrata_z_czynszem") overrideKey = "step_6_utrata_z_czynszem";
                          if (currentStepData.step === 4 && key === "service_base") overrideKey = "step_4_srw";
                          if (currentStepData.step === 5 && key === "capex_for_financing") overrideKey = "step_5_cez";
                          if (currentStepData.step === 1 && key === "tires_base") overrideKey = "step_1_tires_base";
                          if (currentStepData.step === 11 && key === "oferowana_stawka") overrideKey = "step_11_st";
                          if (currentStepData.step === 10 && key === "koszt_mc") overrideKey = "step_10_kdz_koszt_mc";
                          if (currentStepData.step === 9 && key === "koszt_finansowy") overrideKey = "step_9_fi_koszt";

                          // We only show override inputs for numeric values
                          if (typeof val !== 'number') return null;

                          return (
                            <div key={overrideKey} className="flex flex-col">
                              <label className="text-xs text-slate-600 mb-1 font-mono">{overrideKey}</label>
                              <div className="flex shadow-sm rounded-md">
                                <input
                                  type="text"
                                  placeholder={String(val)}
                                  value={overrides[overrideKey] !== undefined ? overrides[overrideKey] : ""}
                                  onChange={(e) => handleOverrideChange(overrideKey, e.target.value)}
                                  className={`flex-1 min-w-0 block w-full px-3 py-2 text-sm border-slate-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 ${overrides[overrideKey] !== undefined ? 'bg-indigo-50 border-indigo-300 text-indigo-900 font-bold' : ''}`}
                                />
                                {overrides[overrideKey] !== undefined && (
                                  <button
                                    onClick={() => handleOverrideChange(overrideKey, "")}
                                    className="ml-2 inline-flex items-center px-2 py-2 border border-transparent text-xs font-medium rounded text-red-700 bg-red-100 hover:bg-red-200"
                                  >
                                    Reset
                                  </button>
                                )}
                              </div>
                            </div>
                          );
                        })}
                     </div>
                     
                     {/* AI CHAT SECTION */}
                     <div className="mt-8">
                       <h4 className="text-xs font-bold uppercase tracking-wider text-purple-600 mb-3 border-b border-purple-200 pb-1 flex items-center">
                         <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                           <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                         </svg>
                         Zapytaj AI o ten krok
                       </h4>
                       <div className="bg-purple-50 p-4 rounded-lg border border-purple-100">
                         <textarea
                           className="w-full text-sm p-3 rounded-md border border-purple-200 focus:ring-2 focus:ring-purple-400 focus:border-purple-400 bg-white placeholder-purple-300"
                           placeholder="Np. Dlaczego stawka za samochód zastępczy wynosi 0?"
                           rows={3}
                           value={currentAiChat.query}
                           onChange={(e) => handleAiQueryChange(activeStep, e.target.value)}
                         />
                         <div className="mt-3 flex justify-end">
                           <button
                             onClick={() => askAi(activeStep)}
                             disabled={currentAiChat.isLoading || !currentAiChat.query?.trim()}
                             className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center"
                           >
                             {currentAiChat.isLoading ? (
                               <>
                                 <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                                   <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                   <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                 </svg>
                                 Myślenie...
                               </>
                             ) : "Zapytaj AI"}
                           </button>
                         </div>
                         
                         {currentAiChat.error && (
                           <div className="mt-4 p-3 bg-red-50 text-red-700 border border-red-200 rounded-md text-xs">
                             {currentAiChat.error}
                           </div>
                         )}

                         {currentAiChat.response && (
                           <div className="mt-4 p-4 bg-white border border-purple-200 rounded-md shadow-sm">
                             <div className="text-xs font-bold text-purple-800 mb-2">Odpowiedź AI:</div>
                             <div className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed prose prose-sm prose-purple max-w-none">
                               {currentAiChat.response}
                             </div>
                           </div>
                         )}
                       </div>
                     </div>
                  </div>
                </div>

              </div>
            ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-400">
                  <p>Wybierz krok z lewej strony, aby rozpocząć analizę.</p>
                </div>
            )}
          </div>
          </>
          )}

        </div>
      </div>
    </div>
  );
}

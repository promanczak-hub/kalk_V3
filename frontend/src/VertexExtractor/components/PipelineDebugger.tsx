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
}

interface DebuggerState {
  status: "idle" | "loading" | "success" | "error";
  steps: DebugStep[];
  error?: string;
}

export function PipelineDebugger({ vehicle, onClose }: PipelineDebuggerProps) {
  const [activeStep, setActiveStep] = useState<number>(1);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [overrides, setOverrides] = useState<Record<string, any>>({});
  const [months, setMonths] = useState<number>(48);
  
  const [state, setState] = useState<DebuggerState>({
    status: "idle",
    steps: []
  });

  const fetchPipeline = async () => {
    setState((s) => ({ ...s, status: "loading", error: undefined }));
    try {
      // Reconstruct payload as done in save & calc
      const payload = {
        base_price_net: vehicle.base_price_net || 0,
        discount_pct: vehicle.discount_pct || 0,
        factory_options: vehicle.factory_options || [],
        service_options: vehicle.service_options || [],
        wibor_pct: vehicle.wibor_pct ?? 5.85,
        margin_pct: vehicle.margin_pct ?? 2.0,
        pricing_margin_pct: vehicle.pricing_margin_pct ?? 15.0,
        depreciation_pct: vehicle.depreciation_pct,
        initial_deposit_pct: vehicle.initial_deposit_pct || 0.0,
        z_oponami: vehicle.z_oponami ?? true,
        klasa_opony_string: vehicle.klasa_opony_string || "Medium",
        srednica_felgi: vehicle.wheels && vehicle.wheels !== "Brak" ? parseInt(vehicle.wheels) : 18,
        korekta_kosztu_opon: vehicle.korekta_kosztu_opon || false,
        koszt_opon_korekta: vehicle.koszt_opon_korekta || 0.0,
        service_cost_type: vehicle.service_cost_type || "ASO",
        okres_bazowy: vehicle.okres_bazowy || 48,
        przebieg_bazowy: vehicle.przebieg_bazowy || 140000,
        replacement_car_enabled: vehicle.replacement_car_enabled ?? true,
        pakiet_serwisowy: vehicle.pakiet_serwisowy || 0.0,
        inne_koszty_serwisowania_netto: vehicle.inne_koszty_serwisowania_netto || 0.0,
        
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

  const currentStepData = state.steps.find((s) => s.step === activeStep);

  return (
    <div className="fixed inset-0 z-[100] bg-slate-900/50 flex flex-col pt-10 px-10 pb-10">
      <div className="bg-white rounded-xl shadow-2xl flex-1 flex flex-col overflow-hidden max-w-7xl w-full mx-auto relative border border-slate-200">
        
        {/* HEADER */}
        <div className="h-16 border-b border-slate-200 flex items-center justify-between px-6 bg-slate-50 shrink-0">
          <div className="flex items-center space-x-4">
            <h2 className="text-lg font-bold text-slate-800">Pipeline Debugger</h2>
            <div className="text-xs px-2 py-1 bg-indigo-100 text-indigo-700 rounded-md font-medium">
              Real Data Mode
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
               className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-1.5 rounded-md text-sm font-medium transition-colors"
             >
               Przelicz z Nadpisaniami
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
                            {Object.entries(currentStepData.outputs).map(([key, val]) => (
                               <tr key={key} className="border-b border-emerald-100/50 last:border-0">
                                 <td className="py-1.5 pr-4 text-emerald-800/70 font-mono text-xs">{key}</td>
                                 <td className="py-1.5 text-right font-semibold text-emerald-900">
                                   {typeof val === 'number' ? val.toLocaleString('pl-PL', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : String(val)}
                                 </td>
                               </tr>
                            ))}
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
                  </div>
                </div>

              </div>
            ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-400">
                  <p>Wybierz krok z lewej strony, aby rozpocząć analizę.</p>
                </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}

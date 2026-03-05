import React, { useState, useEffect } from "react";
import { Euro, Settings2 } from "lucide-react";
import type { FleetVehicleView } from "../types";

// V3 Input Model
export interface CalculatorInputV3 {
  base_price_net: number;
  discount_pct: number;
  factory_options: { name: string; price_net: number }[];
  service_options: { name: string; price_net: number }[];
  
  // RV Metadata
  brand: string;
  model: string;
  version: string;
  engine: string;
  fuel: string;
  transmission: string;
  body_type: string;

  z_oponami: boolean;
  all_season_tires: boolean;
  replacement_car_enabled: boolean;
  wibor_pct: number;
  margin_pct: number;
  initial_deposit_pct: number;
}

interface CalculatorSettingsPanelV3Props {
  vehicle: FleetVehicleView;
  isCalculating?: boolean;
  onCalculate: (payload: CalculatorInputV3) => void;
}

const parseNum = (val: string | number | undefined | null): number => {
  if (typeof val === "number") return val;
  if (!val || val === "Brak") return 0;
  
  let str = val.replace(/\s+/g, "").replace(/[^\d.,-]/g, "");
  if (!str) return 0;

  const hasComma = str.includes(",");
  const hasDot = str.includes(".");
  
  if (hasComma && hasDot) {
    if (str.lastIndexOf(",") > str.lastIndexOf(".")) {
      str = str.replace(/\./g, "").replace(",", ".");
    } else {
      str = str.replace(/,/g, "");
    }
  } else if (hasComma) {
    const parts = str.split(",");
    if (parts.length === 2 && parts[1].length === 3) {
      str = str.replace(",", "");
    } else {
      str = str.replace(",", ".");
    }
  } else if (hasDot) {
    const parts = str.split(".");
    if (parts[parts.length - 1].length === 3) {
      str = str.replace(/\./g, "");
    }
  }
  
  const num = parseFloat(str);
  return isNaN(num) ? 0 : num;
};

export const CalculatorSettingsPanelV3: React.FC<
  CalculatorSettingsPanelV3Props
> = ({ vehicle, isCalculating, onCalculate }) => {
  // Parsed Strings to Numbers State
  const [basePriceNet, setBasePriceNet] = useState<number>(() => {
    const p = parseNum(vehicle.base_price);
    return vehicle.base_price?.toLowerCase().includes("brutto")
      ? Math.round(p / 1.23)
      : Math.round(p);
  });
  const [discountPct, setDiscountPct] = useState<number>(0);

  type PaidOption = { name: string; price: string; category?: string };

  const initialFactoryOpts = (vehicle.paid_options || [])
    .filter((o: PaidOption) => !o.category?.includes("Serwis"))
    .map((o: PaidOption) => ({
      name: o.name,
      price_net: Math.round(
        o.price?.toLowerCase().includes("brutto")
          ? parseNum(o.price) / 1.23
          : parseNum(o.price),
      ),
      selected: true,
    }));

  const initialServiceOpts = (vehicle.paid_options || [])
    .filter((o: PaidOption) => o.category?.includes("Serwis"))
    .map((o: PaidOption) => ({
      name: o.name,
      price_net: Math.round(
        o.price?.toLowerCase().includes("brutto")
          ? parseNum(o.price) / 1.23
          : parseNum(o.price),
      ),
      selected: true,
    }));

  // Options State (Selected by default)
  const [factoryOptions, setFactoryOptions] = useState(initialFactoryOpts);
  const [serviceOptions, setServiceOptions] = useState(initialServiceOpts);

  // LTR V3 Flags
  const [zOponami, setZOponami] = useState(true);
  const [allSeasonTires, setAllSeasonTires] = useState(false);
  const [replacementCar, setReplacementCar] = useState(true);

  // RV Metadata (Editable by user to test scenarios)
  const [brand, setBrand] = useState(vehicle.brand || "");
  const [model, setModel] = useState(vehicle.model || "");
  const [version, setVersion] = useState(vehicle.trim_level || "");
  const [engine, setEngine] = useState(vehicle.powertrain || "");
  const [fuel, setFuel] = useState("");
  const [transmission, setTransmission] = useState("");
  const [bodyType, setBodyType] = useState(vehicle.body_style || "");

  // Finance
  const [wiborPct, setWiborPct] = useState(5.85);
  const [marginPct, setMarginPct] = useState(2.0);
  const [upfrontPct, setUpfrontPct] = useState(0);

  useEffect(() => {
    // Discount logic (Auto extraction attempt) - safe side-effect
    const parsedBase = parseNum(vehicle.base_price);
    const expectedBaseNet = vehicle.base_price?.toLowerCase().includes("brutto")
      ? parsedBase / 1.23
      : parsedBase;

    const baseWithOpts =
      expectedBaseNet +
      initialFactoryOpts.reduce((acc, curr) => acc + curr.price_net, 0) +
      initialServiceOpts.reduce((acc, curr) => acc + curr.price_net, 0);

    const finalExtractedPrice = parseNum(vehicle.final_price_pln);
    const finalExtractedNet = vehicle.final_price_pln?.toLowerCase().includes("brutto")
      ? finalExtractedPrice / 1.23
      : finalExtractedPrice;

    if (finalExtractedNet > 0 && finalExtractedNet < baseWithOpts - 1) {
      const calcDiscount = ((baseWithOpts - finalExtractedNet) / baseWithOpts) * 100;
      setDiscountPct(parseFloat(calcDiscount.toFixed(1)));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicle]);

  const handleCalculateClick = () => {
    const payload: CalculatorInputV3 = {
      base_price_net: basePriceNet,
      discount_pct: discountPct,
      factory_options: factoryOptions
        .filter((o) => o.selected)
        .map((o) => ({ name: o.name, price_net: o.price_net })),
      service_options: serviceOptions
        .filter((o) => o.selected)
        .map((o) => ({ name: o.name, price_net: o.price_net })),
      brand,
      model,
      version,
      engine,
      fuel,
      transmission,
      body_type: bodyType,
      z_oponami: zOponami,
      all_season_tires: allSeasonTires,
      replacement_car_enabled: replacementCar,
      wibor_pct: wiborPct,
      margin_pct: marginPct,
      initial_deposit_pct: upfrontPct,
    };
    onCalculate(payload);
  };

  return (
    <div className="bg-slate-50 border-t border-slate-200 p-5 font-sans">
      <div className="flex items-center gap-2 mb-4">
        <Settings2 className="w-5 h-5 text-blue-600" />
        <h3 className="font-semibold text-slate-800 text-lg">
          Parametry Kalkulatora V3 (Digital Twin)
        </h3>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* LEWA KOLUMNA: Ceny i Opcje */}
        <div className="space-y-6">
          {/* IDENTYFIKACJA RV */}
          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <h4 className="font-medium text-slate-700 mb-3 border-b pb-2">
              Identyfikacja RV
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1 uppercase tracking-wider">Marka</label>
                <input type="text" value={brand} onChange={e => setBrand(e.target.value)} className="w-full px-2 py-1.5 border rounded text-xs focus:ring-1 focus:ring-blue-500 outline-none" placeholder="Marka" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1 uppercase tracking-wider">Model</label>
                <input type="text" value={model} onChange={e => setModel(e.target.value)} className="w-full px-2 py-1.5 border rounded text-xs focus:ring-1 focus:ring-blue-500 outline-none" placeholder="Model" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1 uppercase tracking-wider">Wersja</label>
                <input type="text" value={version} onChange={e => setVersion(e.target.value)} className="w-full px-2 py-1.5 border rounded text-xs focus:ring-1 focus:ring-blue-500 outline-none" placeholder="Wersja" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1 uppercase tracking-wider">Silnik</label>
                <input type="text" value={engine} onChange={e => setEngine(e.target.value)} className="w-full px-2 py-1.5 border rounded text-xs focus:ring-1 focus:ring-blue-500 outline-none" placeholder="Silnik" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1 uppercase tracking-wider">Paliwo</label>
                <input type="text" value={fuel} onChange={e => setFuel(e.target.value)} className="w-full px-2 py-1.5 border rounded text-xs focus:ring-1 focus:ring-blue-500 outline-none" placeholder="Paliwo" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1 uppercase tracking-wider">Skrzynia</label>
                <input type="text" value={transmission} onChange={e => setTransmission(e.target.value)} className="w-full px-2 py-1.5 border rounded text-xs focus:ring-1 focus:ring-blue-500 outline-none" placeholder="Skrzynia" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1 uppercase tracking-wider">Nadwozie</label>
                <input type="text" value={bodyType} onChange={e => setBodyType(e.target.value)} className="w-full px-2 py-1.5 border rounded text-xs focus:ring-1 focus:ring-blue-500 outline-none" placeholder="Nadwozie" />
              </div>
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <h4 className="font-medium text-slate-700 mb-3 border-b pb-2">
              Koszty Pojazdu (Netto)
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-500 mb-1">
                  Cena Bazy Netto
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={basePriceNet}
                    onChange={(e) => setBasePriceNet(Number(e.target.value))}
                    className="w-full pl-3 pr-8 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                  />
                  <span className="absolute right-3 top-2.5 text-slate-400 text-sm">
                    zł
                  </span>
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">
                  Rabat Transakcyjny
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.1"
                    value={discountPct}
                    onChange={(e) => setDiscountPct(Number(e.target.value))}
                    className="w-full pl-3 pr-8 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                  />
                  <span className="absolute right-3 top-2.5 text-slate-400 text-sm">
                    %
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <h4 className="font-medium text-slate-700 mb-3 border-b pb-2">
              Dodatki CAPEX (wliczone w ratę)
            </h4>

            {factoryOptions.length > 0 && (
              <div className="mb-4">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 block">
                  Opcje Fabryczne
                </span>
                <div className="space-y-2 max-h-40 overflow-y-auto pr-2 custom-scrollbar">
                  {factoryOptions.map((opt, idx) => (
                    <label
                      key={idx}
                      className="flex items-center justify-between p-2 hover:bg-slate-50 rounded border border-transparent cursor-pointer transition-colors"
                    >
                      <div className="flex items-center gap-2 overflow-hidden">
                        <input
                          type="checkbox"
                          checked={opt.selected}
                          onChange={(e) => {
                            const newOpts = [...factoryOptions];
                            newOpts[idx].selected = e.target.checked;
                            setFactoryOptions(newOpts);
                          }}
                          className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
                        />
                        <span className="text-sm text-slate-700 truncate min-w-0">
                          {opt.name}
                        </span>
                      </div>
                      <span className="text-sm font-medium text-slate-600 ml-2 whitespace-nowrap">
                        {opt.price_net.toLocaleString()} PLN
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {serviceOptions.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 block">
                  Opcje Serwisowe
                </span>
                <div className="space-y-2 max-h-32 overflow-y-auto pr-2 custom-scrollbar">
                  {serviceOptions.map((opt, idx) => (
                    <label
                      key={idx}
                      className="flex items-center justify-between p-2 hover:bg-slate-50 rounded border border-transparent cursor-pointer transition-colors"
                    >
                      <div className="flex items-center gap-2 overflow-hidden">
                        <input
                          type="checkbox"
                          checked={opt.selected}
                          onChange={(e) => {
                            const newOpts = [...serviceOptions];
                            newOpts[idx].selected = e.target.checked;
                            setServiceOptions(newOpts);
                          }}
                          className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
                        />
                        <span className="text-sm text-slate-700 truncate min-w-0">
                          {opt.name}
                        </span>
                      </div>
                      <span className="text-sm font-medium text-slate-600 ml-2 whitespace-nowrap">
                        {opt.price_net.toLocaleString()} PLN
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}
            
            {factoryOptions.length === 0 && serviceOptions.length === 0 && (
                <p className="text-sm text-slate-500 italic py-2 text-center">Brak wyodrębnionych opcji dodatkowych.</p>
            )}
          </div>
        </div>

        {/* PRAWA KOLUMNA: Parametry finansowe */}
        <div className="space-y-6">
          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <h4 className="font-medium text-slate-700 mb-3 border-b pb-2">
              Parametry Usług LTR (Long-Term Rental)
            </h4>
            <div className="grid grid-cols-3 gap-4">
              <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-slate-50 transition-colors">
                <input
                  type="checkbox"
                  checked={zOponami}
                  onChange={(e) => setZOponami(e.target.checked)}
                  className="w-4 h-4 text-blue-600 mr-3"
                />
                <span className="text-sm text-slate-700">Czy z oponami</span>
              </label>

              <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-slate-50 transition-colors">
                <input
                  type="checkbox"
                  checked={allSeasonTires}
                  onChange={(e) => setAllSeasonTires(e.target.checked)}
                  className="w-4 h-4 text-blue-600 mr-3"
                />
                <span className="text-sm text-slate-700">Opony Całoroczne</span>
              </label>

              <label className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-slate-50 transition-colors">
                <input
                  type="checkbox"
                  checked={replacementCar}
                  onChange={(e) => setReplacementCar(e.target.checked)}
                  className="w-4 h-4 text-blue-600 mr-3"
                />
                <span className="text-sm text-slate-700">Auto Zastępcze</span>
              </label>
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <h4 className="font-medium text-slate-700 mb-3 border-b pb-2">
              Parametry Finansowe
            </h4>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-slate-500 mb-1">
                  WIBOR 1M
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.01"
                    value={wiborPct}
                    onChange={(e) => setWiborPct(Number(e.target.value))}
                    className="w-full pl-2 pr-6 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                  <span className="absolute right-2 top-2 text-slate-400 text-sm">
                    %
                  </span>
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">
                  Marża Fin.
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.1"
                    value={marginPct}
                    onChange={(e) => setMarginPct(Number(e.target.value))}
                    className="w-full pl-2 pr-6 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                  <span className="absolute right-2 top-2 text-slate-400 text-sm">
                    %
                  </span>
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">
                  Wpłata Własna
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="1"
                    value={upfrontPct}
                    onChange={(e) => setUpfrontPct(Number(e.target.value))}
                    className="w-full pl-2 pr-6 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                  <span className="absolute right-2 top-2 text-slate-400 text-sm">
                    %
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* PRZYCISK AKCJI */}
          <div className="pt-4 flex justify-end">
            <button
              onClick={handleCalculateClick}
              disabled={isCalculating}
              className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg shadow-sm transition-colors flex items-center gap-2 transform active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Euro className="w-5 h-5" />
              {isCalculating ? "Wyliczanie..." : "Skalkuluj V3 (Wygeneruj Macierz)"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

import { useState } from "react";
import { Database, Loader2, Check } from "lucide-react";
import { cn } from "../../../lib/utils";
import type { FleetVehicleView } from "../../types";
import { NetGrossInput } from "./NetGrossInput";
import { AccordionCard } from "./AccordionCard";
import { parsePriceToNumber } from "./PriceDualFormat";
import { apiClient } from "../../../lib/apiClient";
import { revalidateVehicleQuiet } from "../../hooks/useRevalidateVehicle";

interface VehicleEquipmentCardProps {
  vehicle: FleetVehicleView;
  // Editable catalog base price (always netto) — punkt wyjścia katalogu.
  // Mieszka tu (Opcje Fabryczne), żeby Analiza Finansowa pokazywała tylko nieedytowalny rozkład.
  catalogBasePriceNet: number;
  setCatalogBasePriceNet: (val: number) => void;
  aiExtractedBasePrice: string | null;
  onRefresh?: () => void;
  // Factory options CRUD
  customFactoryOptions: { id: string; name: string; price_net: number; category: string; no_discount: boolean }[];
  handleUpdateFactoryOptionName: (id: string, newName: string) => void;
  handleUpdateFactoryOptionPrice: (id: string, newVal: number) => void;
  handleUpdateFactoryOptionNoDiscount: (id: string, noDiscount: boolean) => void;
  handleRemoveFactoryOption: (id: string) => void;
  handleAddManualFactoryOption: () => void;
  handleSaveAllOptions: () => Promise<void>;
  isSavingServices: boolean;
  activeDiscountPct: number;
}

const EMPTY = "—";

const VAT = 1.23;

function fmtPLN(value: number): string {
  if (value === 0) return EMPTY;
  return new Intl.NumberFormat("pl-PL", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function VehicleEquipmentCard({
  vehicle,
  catalogBasePriceNet,
  setCatalogBasePriceNet,
  aiExtractedBasePrice,
  onRefresh,
  customFactoryOptions,
  handleUpdateFactoryOptionName,
  handleUpdateFactoryOptionPrice,
  handleUpdateFactoryOptionNoDiscount,
  handleRemoveFactoryOption,
  handleAddManualFactoryOption,
  handleSaveAllOptions,
  isSavingServices,
  activeDiscountPct,
}: VehicleEquipmentCardProps) {
  const [isSavingBasePrice, setIsSavingBasePrice] = useState(false);
  const [basePriceSaveError, setBasePriceSaveError] = useState<string | null>(null);
  const [basePriceJustSaved, setBasePriceJustSaved] = useState(false);

  // Detect source price domain (netto/brutto) to send base_price back in the same
  // domain card_summary already uses. Mirrors the detection in VehicleFinancialOptions.
  const cardSummary = vehicle.synthesis_data?.card_summary as Record<string, unknown> | undefined;
  const detectedPriceDomain = (cardSummary?._price_domain as string) || (cardSummary?.price_domain as string) || "unknown";
  const isSourceNetto = detectedPriceDomain === "netto"
    || (detectedPriceDomain === "unknown" && (vehicle.base_price?.toLowerCase().includes("netto") ?? false));

  // AI-extracted base price (converted to netto for comparison)
  const aiBasePriceRaw = parsePriceToNumber(aiExtractedBasePrice || "0");
  const aiBasePriceNetto = isSourceNetto
    ? aiBasePriceRaw
    : Math.round((aiBasePriceRaw / 1.23) * 100) / 100;
  const basePriceWasEdited = Math.abs(catalogBasePriceNet - aiBasePriceNetto) > 10;

  // Persist the edited base price to card_summary.base_price + re-run validator.
  // We send in the source domain so card_summary stays consistent with the existing
  // price_domain — the editable input is netto, so brutto source requires *1.23.
  const handleSaveBasePrice = async () => {
    if (isSavingBasePrice || catalogBasePriceNet <= 0) return;
    setIsSavingBasePrice(true);
    setBasePriceSaveError(null);
    setBasePriceJustSaved(false);
    try {
      const domain: "netto" | "brutto" = isSourceNetto ? "netto" : "brutto";
      const value = isSourceNetto
        ? catalogBasePriceNet
        : Math.round(catalogBasePriceNet * 1.23);
      const res = await apiClient.fetch(
        `/api/extract/fill-base-price/${vehicle.id}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ base_price: value, domain }),
        },
      );
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`HTTP ${res.status}: ${errText}`);
      }
      await revalidateVehicleQuiet(vehicle.id);
      setBasePriceJustSaved(true);
      onRefresh?.();
      setTimeout(() => setBasePriceJustSaved(false), 2500);
    } catch (e) {
      console.error("save base_price failed:", e);
      setBasePriceSaveError(
        e instanceof Error ? e.message : "Nieznany błąd zapisu",
      );
    } finally {
      setIsSavingBasePrice(false);
    }
  };

  const standardEquipment = vehicle.standard_equipment ?? [];
  const hasStandardEquipment = standardEquipment.length > 0;

  // Calculate total — options are always stored as netto (price_net),
  // so brutto is always netto × VAT regardless of base_price domain
  const totalNet = customFactoryOptions.reduce((sum, opt) => sum + opt.price_net, 0);
  const totalBrutto = totalNet * VAT;

  const titleNode = (
    <div className="flex items-center">
      Opcje fabryczne
      {customFactoryOptions.length > 0 && (
        <span className="ml-2 text-slate-400">({customFactoryOptions.length})</span>
      )}
    </div>
  );

  return (
    <AccordionCard title={titleNode} id="factory-options-section" defaultOpen={false}>
      <div className="space-y-4">
        {/* Cena bazowa katalogowa — punkt wyjścia katalogu (edytowalna).
            Przeniesiona tu z Analizy Finansowej, która pokazuje już tylko nieedytowalny rozkład. */}
        <div className="pb-4 border-b border-slate-200">
          <div className="flex items-center gap-1.5 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Cena bazowa katalogowa</span>
            {basePriceWasEdited && (
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 uppercase tracking-wider">edytowano</span>
            )}
          </div>
          <div className="flex w-full justify-between items-center gap-2 flex-wrap">
            <NetGrossInput
              netValue={catalogBasePriceNet}
              onChangeNet={setCatalogBasePriceNet}
            />
            {basePriceWasEdited && (
              <div className="flex flex-col items-end gap-0.5">
                <button
                  type="button"
                  onClick={handleSaveBasePrice}
                  disabled={isSavingBasePrice || catalogBasePriceNet <= 0}
                  className={cn(
                    "inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-bold uppercase tracking-wider transition-colors disabled:opacity-60 disabled:cursor-not-allowed",
                    basePriceJustSaved
                      ? "bg-emerald-100 text-emerald-700 border border-emerald-300"
                      : "bg-blue-600 text-white hover:bg-blue-700 border border-blue-700",
                  )}
                  title={
                    basePriceJustSaved
                      ? "Zapisano w bazie — kalkulator przeliczy po odświeżeniu"
                      : "Zapisz cenę do bazy (card_summary.base_price) i przelej do kalkulatora"
                  }
                  data-testid="save-base-price-button"
                >
                  {isSavingBasePrice ? (
                    <>
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Zapisuję…
                    </>
                  ) : basePriceJustSaved ? (
                    <>
                      <Check className="w-3 h-3" />
                      Zapisano
                    </>
                  ) : (
                    <>
                      <Check className="w-3 h-3" />
                      Zapisz cenę
                    </>
                  )}
                </button>
                {basePriceSaveError && (
                  <span className="text-[9px] text-red-600 max-w-[220px] text-right leading-tight">
                    {basePriceSaveError}
                  </span>
                )}
              </div>
            )}
          </div>
          {aiExtractedBasePrice && basePriceWasEdited && (
            <span className="inline-block text-[10px] text-amber-600 leading-tight mt-2 bg-amber-50 p-1 rounded border border-amber-100">
              Wartość odczytana: <b>{aiExtractedBasePrice}</b>
              <button
                type="button"
                className="ml-1.5 text-blue-600 hover:text-blue-800 underline cursor-pointer font-semibold"
                onClick={() => setCatalogBasePriceNet(aiBasePriceNetto)}
              >
                Przywróć
              </button>
            </span>
          )}
        </div>

        {/* Editable options list */}
        {customFactoryOptions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-slate-200">
                  <th className="text-left text-xs font-semibold uppercase tracking-wider text-slate-400 py-3 pr-4">
                    Nazwa
                  </th>
                  <th className="text-right text-xs font-semibold uppercase tracking-wider text-slate-400 py-3 pr-2 w-40">
                    Netto
                  </th>
                  <th className="text-center text-xs font-semibold uppercase tracking-wider text-slate-400 py-3 w-6">
                  </th>
                  <th className="text-right text-xs font-semibold uppercase tracking-wider text-slate-400 py-3 pr-2 w-40">
                    Brutto
                  </th>
                  <th className="w-20"></th>
                </tr>
              </thead>
              <tbody>
                {customFactoryOptions.map((opt) => (
                  <tr
                    key={opt.id}
                    className="border-b border-slate-100 last:border-b-0"
                  >
                    <td className="py-2.5 pr-4">
                      <div className="flex items-center gap-2">
                         <input
                          type="text"
                          className="flex-1 px-2.5 py-1.5 border border-slate-200 rounded text-slate-700 font-medium text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                          value={opt.name}
                          onChange={(e) => handleUpdateFactoryOptionName(opt.id, e.target.value)}
                          placeholder="Nazwa opcji"
                        />
                        {opt.no_discount && (
                          <span className="shrink-0 px-1.5 py-0.5 text-[9px] font-bold uppercase rounded bg-amber-50 text-amber-700 border border-amber-200">
                            Nierabatowana
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-2.5" colSpan={3}>
                      <NetGrossInput
                        netValue={opt.price_net}
                        onChangeNet={(newVal) => handleUpdateFactoryOptionPrice(opt.id, newVal)}
                      />
                    </td>
                    <td className="py-2.5 text-center">
                      <div className="flex items-center gap-1">
                        <label
                          className="relative inline-flex items-center cursor-pointer"
                          title={opt.no_discount ? "Opcja nierabatowana — kliknij aby zmienić" : "Kliknij aby oznaczyć jako nierabatowaną"}
                        >
                          <input
                            type="checkbox"
                            className="sr-only peer"
                            checked={opt.no_discount}
                            onChange={(e) => handleUpdateFactoryOptionNoDiscount(opt.id, e.target.checked)}
                          />
                          <div className="w-7 h-4 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-amber-500"></div>
                        </label>
                        <button
                          onClick={() => handleRemoveFactoryOption(opt.id)}
                          className="p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                          title="Usuń opcję"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-4 text-center text-slate-400 text-sm">
            Brak opcji fabrycznych — kliknij „Dodaj ręcznie" poniżej.
          </div>
        )}

        {/* Totals */}
        {customFactoryOptions.length > 0 && (
          <div className="pt-3 border-t border-slate-200 flex flex-wrap justify-between items-baseline gap-2">
            <span className="text-xs text-slate-400">
               Suma opcji fabrycznych
              {activeDiscountPct > 0 && (
                <span className="ml-2 px-1.5 py-0.5 text-[9px] font-bold uppercase rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Rabatowany ({activeDiscountPct}%)
                </span>
              )}
              {activeDiscountPct === 0 && (
                <span className="ml-2 px-1.5 py-0.5 text-[9px] font-bold uppercase rounded bg-slate-50 text-slate-500 border border-slate-200">
                  Nierabatowany
                </span>
              )}
            </span>
            <div className="text-right">
              <span className="text-sm font-semibold text-slate-800 tabular-nums">
                {fmtPLN(totalBrutto)} PLN
              </span>
              <span className="text-xs text-slate-400 ml-2 tabular-nums">
                ({fmtPLN(totalNet)} netto)
              </span>
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <button
            onClick={handleAddManualFactoryOption}
            className="flex items-center text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 hover:bg-slate-100 transition-all shadow-sm"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            Dodaj ręcznie
          </button>
          <button
            onClick={handleSaveAllOptions}
            disabled={isSavingServices}
            className="flex items-center justify-center text-xs font-semibold px-6 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-all shadow-sm"
            title="Zapisuje opcje fabryczne i serwisowe do bazy"
          >
            {isSavingServices ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Database className="w-4 h-4 mr-2" />}
            {isSavingServices ? "Zapisywanie..." : "Zapisz zmiany"}
          </button>
        </div>

        {/* Standard Equipment (collapsed) */}
         {hasStandardEquipment && (
          <AccordionCard title={`Wyposażenie standardowe (${standardEquipment.length})`} defaultOpen={false} className="mt-4 border-slate-100 shadow-none">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1">
              {standardEquipment.map((item, idx) => (
                <div
                  key={`${item}-${idx}`}
                  className="py-1.5 text-xs text-slate-600 border-b border-slate-50"
                >
                  {item}
                </div>
              ))}
            </div>
          </AccordionCard>
        )}
      </div>
    </AccordionCard>
  );
}

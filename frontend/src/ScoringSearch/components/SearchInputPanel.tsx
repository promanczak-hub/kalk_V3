import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Loader2, Sparkles, X } from 'lucide-react';
import { Box } from '@mui/material';
import type { SearchContext, SelectedFeature, InitialDataResponse } from '../types';
import { useEmailExtraction } from '../hooks/useEmailExtraction';

interface SearchInputPanelProps {
  searchContext: SearchContext;
  onContextChange: (ctx: SearchContext) => void;
  setSelectedFeatures: (features: SelectedFeature[]) => void;
  initialData: InitialDataResponse | null;
}

const formatPLN = (n: number): string => n.toLocaleString('pl-PL');

export const SearchInputPanel: React.FC<SearchInputPanelProps> = ({
  searchContext,
  onContextChange,
  setSelectedFeatures,
  initialData,
}) => {
  const knownBrands = initialData?.brands || [];
  const brandModelMap = initialData?.brand_model_map || {};
  const knownBodyTypes = (initialData?.body_types || []).map((bt) => bt.name);

  const [expanded, setExpanded] = useState(true);

  const {
    emailText: queryText,
    setEmailText: setQueryText,
    extracting,
    error: extractError,
    lastSummary,
    extract,
    clearSummary,
  } = useEmailExtraction({
    searchContext,
    setSearchContext: onContextChange,
    setSelectedFeatures,
    knownBrands,
    brandModelMap,
    knownBodyTypes,
  });

  return (
    <Box sx={{ p: 2, pb: 1 }}>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between gap-1.5 mb-2 px-1 py-0.5 -mx-1 rounded hover:bg-slate-50 transition-colors"
        aria-expanded={expanded}
        aria-controls="opisz-auto-content"
      >
        <span className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-blue-600" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-700">
            Opisz auto
          </span>
          {!expanded && queryText.trim() && (
            <span className="text-[10px] text-slate-400 font-normal normal-case truncate max-w-[160px]">
              · {queryText.trim().slice(0, 40)}{queryText.trim().length > 40 ? '…' : ''}
            </span>
          )}
        </span>
        {expanded ? (
          <ChevronUp className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
        )}
      </button>
      <div id="opisz-auto-content" className="flex flex-col gap-2">
        {expanded && (
          <>
            <textarea
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              placeholder={
                "Opisz czego szukasz — albo wklej email od klienta.\n\n" +
                "Np. 'czerwony SUV premium z dużą mocą' lub:\n" +
                "Skoda Kodiaq Drive 2.0 TSI 204KM lub VW Tayron, automat, kamera cofania, " +
                "podgrzewane szyby (jeśli dostępne). Budżet 670 EUR/mc, limit 90 tys."
              }
              className="w-full text-xs p-3 border border-slate-300 hover:border-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-100 rounded-md outline-none resize-none bg-white transition-colors h-40"
              disabled={extracting}
            />
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10px] text-slate-500">
                AI rozpozna marki, modele, wersje, budżet, przebieg i wymagania → wstawi do filtrów
              </span>
              <button
                type="button"
                onClick={extract}
                disabled={extracting || !queryText.trim()}
                className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-md shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {extracting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Analizuję...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" /> Analizuj
                  </>
                )}
              </button>
            </div>
            {extractError && (
              <div className="text-[11px] text-red-700 bg-red-50 border border-red-200 px-2 py-1 rounded-md">
                Błąd: {extractError}
              </div>
            )}
          </>
        )}
        {lastSummary && (
          <div className="relative text-[11px] text-emerald-900 bg-emerald-50 border border-emerald-200 px-2.5 py-1.5 rounded-md pr-7">
            <button
              type="button"
              onClick={clearSummary}
              className="absolute top-1 right-1 text-emerald-600 hover:text-emerald-900"
              title="Schowaj podsumowanie"
            >
              <X className="w-3.5 h-3.5" />
            </button>
            <div className="font-semibold mb-0.5">Wstawiono do filtrów:</div>
            <ul className="space-y-0.5">
              {lastSummary.brands.length > 0 && (
                <li>
                  Marki: <span className="font-mono">{lastSummary.brands.join(', ')}</span>
                </li>
              )}
              {lastSummary.models.length > 0 && (
                <li>
                  Modele: <span className="font-mono">{lastSummary.models.join(', ')}</span>
                </li>
              )}
              {lastSummary.trims.length > 0 && (
                <li>
                  Wersje: <span className="font-mono">{lastSummary.trims.join(', ')}</span>
                </li>
              )}
              {lastSummary.bodyTypes.length > 0 && (
                <li>
                  Typ nadwozia: <span className="font-mono">{lastSummary.bodyTypes.join(', ')}</span>
                </li>
              )}
              {lastSummary.budget && (
                <li>
                  Budżet: <span className="font-mono">{formatPLN(lastSummary.budget)} PLN/mc</span>
                </li>
              )}
              {lastSummary.durationMonths && (
                <li>
                  Okres: <span className="font-mono">{lastSummary.durationMonths} mc</span>
                </li>
              )}
              {lastSummary.annualMileage && (
                <li>
                  Roczny przebieg: <span className="font-mono">{formatPLN(lastSummary.annualMileage)} km</span>
                </li>
              )}
              {lastSummary.featuresCount > 0 && (
                <li>
                  Cechy preferowane:{' '}
                  <span className="font-mono">{lastSummary.featuresCount}</span>
                  <span className="text-emerald-700 ml-1">
                    (boost rankingu wektorowego, bez twardego filtrowania)
                  </span>
                </li>
              )}
              {lastSummary.semanticHint && (
                <li className="italic text-emerald-800">
                  Wektor semantyczny: "{lastSummary.semanticHint}"
                </li>
              )}
              <li className="text-[10px] text-emerald-700 italic mt-1">
                💡 Wektor: cały tekst zostaje wysłany do AI search (mieszane vector spaces: use case + specs + equipment).
              </li>
            </ul>
            {(lastSummary.unmatchedBrands.length > 0 || lastSummary.unmatchedModels.length > 0) && (
              <div className="mt-1 text-amber-800">
                Nieznalezione w bazie: {[...lastSummary.unmatchedBrands, ...lastSummary.unmatchedModels].join(', ')}
              </div>
            )}
          </div>
        )}
        {/* "Niekompletne dane" chip — shows the UI defaults that fill in for
            anything the AI didn't extract, plus an explicit signal that
            auto-fit will pick the best matrix variant per vehicle if budget
            is set but duration/mileage aren't. */}
        {lastSummary && (() => {
          const missing: string[] = [];
          if (!lastSummary.durationMonths) missing.push(`${searchContext.exact_duration_months} mc`);
          if (!lastSummary.annualMileage) {
            const annual = Math.round((searchContext.exact_total_mileage * 12) / Math.max(searchContext.exact_duration_months, 1));
            missing.push(`${formatPLN(annual)} km/rok`);
          }
          if (!searchContext.ai_supplied_margin) missing.push(`marża ${searchContext.margin_pct ?? 10}%`);
          if (missing.length === 0) return null;
          const autoFitOn = !!searchContext.fit_to_budget;
          return (
            <div className="text-[11px] text-amber-900 bg-amber-50 border border-amber-200 px-2.5 py-1.5 rounded-md">
              <div className="font-semibold mb-0.5">⚠️ Niekompletne dane — założono:</div>
              <div className="font-mono text-[11px] leading-snug">
                {missing.join(' · ')}
              </div>
              {autoFitOn ? (
                <div className="mt-1 text-[10px] text-emerald-800 italic">
                  ✨ Auto-fit aktywny: dla każdego pojazdu serwer wybierze najtańszy wariant matrix i marżę
                  maksymalizującą zysk w budżecie {formatPLN(lastSummary.budget ?? 0)} PLN/mc.
                </div>
              ) : (
                <div className="mt-1 text-[10px] text-amber-800 italic">
                  Zmień suwakami w sekcji KALKULACJE (MATRIX) jeśli inne wartości.
                </div>
              )}
            </div>
          );
        })()}
      </div>
    </Box>
  );
};

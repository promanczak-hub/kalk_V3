import React, { useState } from 'react';
import { Mail, Loader2, Sparkles, X } from 'lucide-react';
import { Box, TextField, InputAdornment, IconButton, Tooltip } from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import ClearIcon from '@mui/icons-material/Clear';
import type { SearchContext, SelectedFeature, InitialDataResponse } from '../types';
import { useEmailExtraction } from '../hooks/useEmailExtraction';

interface SearchInputPanelProps {
  searchContext: SearchContext;
  onContextChange: (ctx: SearchContext) => void;
  setSelectedFeatures: (features: SelectedFeature[]) => void;
  initialData: InitialDataResponse | null;
}

type Tab = 'search' | 'email';

const formatPLN = (n: number): string => n.toLocaleString('pl-PL');

export const SearchInputPanel: React.FC<SearchInputPanelProps> = ({
  searchContext,
  onContextChange,
  setSelectedFeatures,
  initialData,
}) => {
  const [activeTab, setActiveTab] = useState<Tab>('search');
  const [localQuery, setLocalQuery] = useState(searchContext.semanticQuery || '');
  const isTyping = React.useRef(false);

  const knownBrands = initialData?.brands || [];
  const brandModelMap = initialData?.brand_model_map || {};

  const {
    emailText,
    setEmailText,
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
  });

  React.useEffect(() => {
    if (!searchContext.semanticQuery && !isTyping.current) {
      setLocalQuery('');
    }
  }, [searchContext.semanticQuery]);

  React.useEffect(() => {
    const handler = setTimeout(() => {
      if (searchContext.semanticQuery !== localQuery) {
        onContextChange({ ...searchContext, semanticQuery: localQuery });
        isTyping.current = false;
      }
    }, 600);
    return () => clearTimeout(handler);
  }, [localQuery, searchContext, onContextChange]);

  const handleClearSemantic = () => {
    setLocalQuery('');
    onContextChange({ ...searchContext, semanticQuery: '' });
  };

  return (
    <Box sx={{ p: 2, pb: 1 }}>
      {/* Tab switcher */}
      <div className="flex items-center gap-1 mb-2 bg-slate-100 rounded-lg p-1 w-fit">
        <button
          type="button"
          onClick={() => setActiveTab('search')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            activeTab === 'search'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-200'
          }`}
        >
          <Sparkles className="w-3 h-3" />
          Opisz auto
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('email')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            activeTab === 'email'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-200'
          }`}
        >
          <Mail className="w-3 h-3" />
          Email klienta
        </button>
      </div>

      {activeTab === 'search' ? (
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Opisz auto (np. 'czerwony SUV premium z dużą mocą...')"
          value={localQuery}
          onChange={(e) => setLocalQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Tooltip title="Wyszukiwanie wspierane przez AI (Gemini)">
                  <AutoAwesomeIcon sx={{ color: 'primary.main' }} />
                </Tooltip>
              </InputAdornment>
            ),
            endAdornment: localQuery ? (
              <InputAdornment position="end">
                <IconButton size="small" onClick={handleClearSemantic}>
                  <ClearIcon fontSize="small" />
                </IconButton>
              </InputAdornment>
            ) : null,
            sx: {
              borderRadius: 2,
              bgcolor: 'background.paper',
              '&.Mui-focused': { boxShadow: '0 0 0 2px rgba(59, 130, 246, 0.5)' },
            },
          }}
        />
      ) : (
        <div className="flex flex-col gap-2">
          <textarea
            value={emailText}
            onChange={(e) => setEmailText(e.target.value)}
            placeholder={
              "Wklej treść maila od klienta (temat + treść).\n\n" +
              "Np. Dzień dobry, prośba o oferty: Skoda Kodiaq 2.0 TSI lub VW Tayron, automat, " +
              "benzyna, kamera cofania. Budżet 650-670 EUR/mc, limit 90 tys km."
            }
            className="w-full text-xs p-3 border border-slate-300 hover:border-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-100 rounded-md outline-none resize-none bg-white transition-colors h-40"
            disabled={extracting}
          />
          <div className="flex items-center justify-between gap-2">
            <span className="text-[10px] text-slate-500">
              AI wyciągnie marki, modele, budżet, przebieg i wymagania → wstawi do filtrów
            </span>
            <button
              type="button"
              onClick={extract}
              disabled={extracting || !emailText.trim()}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-md shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {extracting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Analizuję...
                </>
              ) : (
                <>
                  <Mail className="w-3.5 h-3.5" /> Analizuj email
                </>
              )}
            </button>
          </div>
          {extractError && (
            <div className="text-[11px] text-red-700 bg-red-50 border border-red-200 px-2 py-1 rounded-md">
              Błąd: {extractError}
            </div>
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
                  <li>Wymagania: <span className="font-mono">{lastSummary.featuresCount}</span></li>
                )}
              </ul>
              {(lastSummary.unmatchedBrands.length > 0 || lastSummary.unmatchedModels.length > 0) && (
                <div className="mt-1 text-amber-800">
                  Nieznalezione w bazie: {[...lastSummary.unmatchedBrands, ...lastSummary.unmatchedModels].join(', ')}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </Box>
  );
};

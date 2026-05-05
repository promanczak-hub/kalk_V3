import React from 'react';
import { Snackbar, Alert } from '@mui/material';
import { Loader2 } from 'lucide-react';
import { SearchInputPanel } from './components/SearchInputPanel';
import { ScoringFilters } from './components/ScoringFilters';
import { ScoringResults } from './components/ScoringResults';
import { useScoringSearch } from './hooks/useScoringSearch';
import { useInitialData } from './hooks/useInitialData';

export const ScoringSearchPage: React.FC = () => {
  const {
    searchContext,
    setSearchContext,
    selectedFeatures,
    setSelectedFeatures,
    searchResults,
    isSearching,
    snackbarMessage,
    setSnackbarMessage,
    computedRequirements
  } = useScoringSearch();

  const { initialData } = useInitialData();

  return (
    <div className="flex flex-col md:flex-row gap-4 md:h-[calc(100vh-120px)]">
      {/* Left Column - Filters */}
      <aside className="w-full md:w-80 flex-shrink-0 md:h-full">
        <div className="h-full overflow-hidden flex flex-col bg-white border border-slate-200 rounded-lg shadow-sm">
          {/* Sidebar header - Material elevation */}
          <div className="px-4 py-3 border-b border-slate-200 bg-white flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                Szukaj Pojazdów
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Opisz auto lub wybierz filtry
              </p>
            </div>
          </div>
          {/* Shared scroll container: input panel + filters scroll together so
              the slider section at the bottom stays reachable even when the
              "Wstawiono do filtrów" / "Niekompletne dane" chips push content
              down. Previously SearchInputPanel had no flex-shrink, so it ate
              all the vertical space and left ScoringFilters with ~1cm of
              scroll. */}
          <div className="flex-grow overflow-y-auto">
            <SearchInputPanel
              searchContext={searchContext}
              onContextChange={setSearchContext}
              setSelectedFeatures={setSelectedFeatures}
              initialData={initialData}
            />
            <ScoringFilters
              searchContext={searchContext}
              onContextChange={setSearchContext}
              selectedFeatures={selectedFeatures}
              onFeaturesChange={setSelectedFeatures}
              searchResults={searchResults}
            />
          </div>
        </div>
      </aside>

      {/* Right Column - Results */}
      <section className="flex-grow flex flex-col h-full">
        <div className="h-full flex flex-col overflow-hidden bg-white border border-slate-200 rounded-lg shadow-sm">
          <div className="px-4 py-3 border-b border-slate-200 bg-white flex justify-between items-center">
            <div className="flex items-center gap-3">
              <h2 className="text-base font-semibold text-slate-900">
                Wyniki Dopasowania
              </h2>
              <span className="text-xs font-semibold text-blue-700 bg-blue-100 px-2.5 py-0.5 rounded-full">
                {searchResults.length}
              </span>
              {isSearching && <Loader2 className="w-4 h-4 animate-spin text-blue-600" />}
            </div>
          </div>

          <div className="p-4 flex-grow overflow-y-auto bg-slate-50">
            <ScoringResults
              results={searchResults}
              loading={isSearching}
              searchContext={searchContext}
              selectedFeatures={selectedFeatures}
              requirements={computedRequirements}
            />
          </div>
        </div>
      </section>

      <Snackbar open={!!snackbarMessage} autoHideDuration={6000} onClose={() => setSnackbarMessage(null)}>
        <Alert onClose={() => setSnackbarMessage(null)} severity="info" sx={{ width: '100%', borderRadius: '6px' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </div>
  );
};

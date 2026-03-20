import { Search, Loader2 } from "lucide-react";
import { useReverseSearch } from "../hooks/useReverseSearch";
import { useVertexExtraction } from "../hooks/useVertexExtraction";
import { VertexExtractArea } from "./VertexExtractArea";
import { ReverseSearchFilters } from "./ReverseSearchFilters";
import { ReverseSearchResults } from "./ReverseSearchResults";

export function ReverseSearchPage() {
  const reverseSearch = useReverseSearch();
  const vertexExtraction = useVertexExtraction(
    reverseSearch.state.catalog,
    reverseSearch.actions.handleExtractionSuccess
  );

  if (reverseSearch.state.loading) {
    return (
      <div className="flex items-center justify-center py-20 text-slate-400">
        <Loader2 className="w-6 h-6 animate-spin mr-3" />
        <span>{"Ładowanie katalogu cech..."}</span>
      </div>
    );
  }

  return (
    <div className="max-w-[1400px] mx-auto pb-12">
      {/* Page header */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
           <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
             <Search className="w-5 h-5 text-indigo-600" />
             Reverse Search — Wyszukiwanie po cechach
           </h1>
           <p className="text-sm text-slate-500 mt-1">
             Znajdź pojazdy metodą odwróconą za pomocą filtrów sprzętowych albo asystenta AI.
           </p>
        </div>
      </div>

      {/* Global Live Search */}
      <div className="mb-6">
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-slate-400" />
          </div>
          <input
            type="text"
            value={reverseSearch.state.globalSearchQuery}
            onChange={(e) => reverseSearch.actions.setGlobalSearchQuery(e.target.value)}
            className="block w-full pl-11 pr-4 py-4 bg-white border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-lg shadow-sm"
            placeholder="Szukaj swobodnie... np. diesel kombi automatyczna klimatyzacja matrix"
          />
        </div>
      </div>

      {/* AI Assistant Banner */}
      <VertexExtractArea 
        extractionText={vertexExtraction.extractionText}
        setExtractionText={vertexExtraction.setExtractionText}
        extracting={vertexExtraction.extracting}
        handleExtraction={vertexExtraction.handleExtraction}
      />

      <div className="flex gap-6">
        {/* ── Left: Filter Sidebar ── */}
        <ReverseSearchFilters 
            state={reverseSearch.state} 
            actions={reverseSearch.actions} 
         />

        {/* ── Right: Results ── */}
        <ReverseSearchResults 
            state={reverseSearch.state} 
            actions={reverseSearch.actions} 
         />
      </div>
    </div>
  );
}

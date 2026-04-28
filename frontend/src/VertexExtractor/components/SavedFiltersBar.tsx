import { useState } from "react";
import { Bookmark, BookmarkPlus, ChevronDown, Trash2, Check, Loader2, X } from "lucide-react";
import { useSavedFilters, type ReverseSearchFilterState, type SavedFilter } from "../hooks/useSavedFilters";

interface SavedFiltersBarProps {
  currentState: ReverseSearchFilterState;
  onLoad: (state: ReverseSearchFilterState) => void;
  userEmail?: string | null;
}

function summarizeState(s: ReverseSearchFilterState): string {
  const parts: string[] = [];
  if (s.globalSearchQuery) parts.push(`"${s.globalSearchQuery.slice(0, 24)}${s.globalSearchQuery.length > 24 ? "…" : ""}"`);
  if (s.activeFilters && s.activeFilters.length > 0) parts.push(`${s.activeFilters.length} cech`);
  if (s.bodyTypes && s.bodyTypes.length > 0) parts.push(`${s.bodyTypes.length} nadwozi`);
  if (s.vehicleScope && s.vehicleScope !== "all") parts.push(s.vehicleScope === "passenger" ? "osobowe" : "ciężarowe");
  if (typeof s.priceMax === "number" && s.priceMax > 0) parts.push(`do ${s.priceMax} PLN`);
  if (s.priceMonths) parts.push(`${s.priceMonths}m-cy`);
  if (s.priceMileage) parts.push(`${(s.priceMileage / 1000)}k km`);
  return parts.length > 0 ? parts.join(" · ") : "(pusto)";
}

export function SavedFiltersBar({ currentState, onLoad, userEmail }: SavedFiltersBarProps) {
  const { items, loading, error, save, remove } = useSavedFilters(userEmail);
  const [showSaveForm, setShowSaveForm] = useState(false);
  const [showList, setShowList] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const hasAnyFilter =
    !!currentState.globalSearchQuery ||
    (currentState.activeFilters?.length ?? 0) > 0 ||
    (currentState.bodyTypes?.length ?? 0) > 0 ||
    (currentState.vehicleScope && currentState.vehicleScope !== "all") ||
    currentState.priceMin !== "" ||
    currentState.priceMax !== "";

  const handleSave = async () => {
    setSaveError(null);
    if (!saveName.trim()) {
      setSaveError("Podaj nazwę.");
      return;
    }
    setSaving(true);
    const item = await save(saveName, currentState);
    setSaving(false);
    if (item) {
      setSaveName("");
      setShowSaveForm(false);
    } else {
      setSaveError("Nie udało się zapisać.");
    }
  };

  const handleLoad = (f: SavedFilter) => {
    onLoad(f.filter_state);
    setShowList(false);
  };

  return (
    <div className="mb-4 flex items-center gap-2 flex-wrap">
      {/* Save button + inline form */}
      <div className="relative">
        <button
          type="button"
          onClick={() => {
            setShowSaveForm((v) => !v);
            setShowList(false);
          }}
          disabled={!hasAnyFilter}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[11px] font-medium bg-white border border-slate-200 hover:bg-indigo-50 hover:border-indigo-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          title={hasAnyFilter ? "Zapisz aktualne filtry" : "Najpierw ustaw filtry"}
        >
          <BookmarkPlus className="w-3.5 h-3.5 text-indigo-600" />
          Zapisz
        </button>

        {showSaveForm && (
          <div className="absolute top-full left-0 mt-1 z-20 bg-white border border-slate-200 rounded-lg shadow-lg p-3 w-72">
            <div className="text-[11px] font-semibold text-slate-700 mb-1.5">
              Zapisz zestaw filtrów
            </div>
            <div className="text-[10px] text-slate-400 mb-2 truncate">
              {summarizeState(currentState)}
            </div>
            <input
              type="text"
              value={saveName}
              onChange={(e) => setSaveName(e.target.value)}
              placeholder="np. klient X — flota osobowa"
              className="w-full text-xs px-2 py-1.5 border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSave();
                if (e.key === "Escape") setShowSaveForm(false);
              }}
            />
            {saveError && (
              <div className="text-[10px] text-rose-600 mt-1">{saveError}</div>
            )}
            <div className="flex justify-end gap-1.5 mt-2">
              <button
                type="button"
                onClick={() => setShowSaveForm(false)}
                className="px-2 py-1 text-[11px] text-slate-600 hover:bg-slate-100 rounded"
              >
                Anuluj
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving || !saveName.trim()}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 rounded transition-colors"
              >
                {saving ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Check className="w-3 h-3" />
                )}
                Zapisz
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Load dropdown */}
      <div className="relative">
        <button
          type="button"
          onClick={() => {
            setShowList((v) => !v);
            setShowSaveForm(false);
          }}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[11px] font-medium bg-white border border-slate-200 hover:bg-indigo-50 hover:border-indigo-300 transition-colors"
          title="Wczytaj zapisany filtr"
        >
          <Bookmark className="w-3.5 h-3.5 text-indigo-600" />
          Zapisane
          {items.length > 0 && (
            <span className="text-[10px] text-slate-500 ml-0.5">({items.length})</span>
          )}
          <ChevronDown className="w-3 h-3 text-slate-400" />
        </button>

        {showList && (
          <div className="absolute top-full left-0 mt-1 z-20 bg-white border border-slate-200 rounded-lg shadow-lg w-96 max-h-80 overflow-auto">
            <div className="flex items-center justify-between px-3 py-2 border-b border-slate-100">
              <span className="text-[11px] font-semibold text-slate-700">
                Zapisane filtry
              </span>
              <button
                type="button"
                onClick={() => setShowList(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
            {loading && (
              <div className="px-3 py-4 text-center text-[11px] text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin mx-auto mb-1" />
                Wczytuję...
              </div>
            )}
            {!loading && items.length === 0 && (
              <div className="px-3 py-6 text-center text-[11px] text-slate-400">
                Brak zapisanych filtrów. Ustaw filtry i kliknij &quot;Zapisz&quot;.
              </div>
            )}
            {!loading && items.length > 0 && (
              <ul className="divide-y divide-slate-100">
                {items.map((f) => (
                  <li key={f.id} className="hover:bg-slate-50 transition-colors">
                    <div className="flex items-center justify-between gap-2 px-3 py-2">
                      <button
                        type="button"
                        onClick={() => handleLoad(f)}
                        className="flex-1 text-left min-w-0"
                        title="Wczytaj"
                      >
                        <div className="text-xs font-medium text-slate-700 truncate">
                          {f.name}
                        </div>
                        <div className="text-[10px] text-slate-400 truncate">
                          {summarizeState(f.filter_state)}
                        </div>
                      </button>
                      {confirmDeleteId === f.id ? (
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={async () => {
                              await remove(f.id);
                              setConfirmDeleteId(null);
                            }}
                            className="text-[10px] font-semibold text-rose-600 hover:text-rose-800"
                          >
                            Tak
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmDeleteId(null)}
                            className="text-[10px] text-slate-500 hover:text-slate-700"
                          >
                            Nie
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setConfirmDeleteId(f.id)}
                          className="text-slate-300 hover:text-rose-600 p-1"
                          title="Usuń"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
            {error && (
              <div className="px-3 py-2 text-[10px] text-rose-600 border-t border-slate-100">
                {error}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

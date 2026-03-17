import { useState, useEffect } from "react";
import { apiFetch } from "../../../lib/api";
import { X, Loader2, Plus, Check } from "lucide-react";

interface FeaturePreview {
  feature_key: string;
  value_bool: boolean | null;
  value_num: number | null;
  value_text: string | null;
  unit: string | null;
  mapping_confidence: number;
}

interface PreviewResponse {
  status: string;
  matched_variant: string;
  confidence: number;
  reasoning: string;
  features: FeaturePreview[];
  error?: string;
}

interface ModalProps {
  vehicleId: string;
  catalogId: string;
  catalogName: string;
  onClose: () => void;
  onSuccess: () => void;
}

export function CatalogFeatureSelectorModal({
  vehicleId,
  catalogId,
  catalogName,
  onClose,
  onSuccess,
}: ModalProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PreviewResponse | null>(null);
  
  // Set of selected feature keys
  const [selectedFeatures, setSelectedFeatures] = useState<Set<string>>(new Set());

  useEffect(() => {
    async function loadPreview() {
      try {
        const res = await apiFetch(`/api/features/vehicle/${vehicleId}/catalog-preview?catalog_id=${catalogId}`);
        if (!res.ok) throw new Error("Błąd podczas ładowania podglądu z cennika");
        
        const json: PreviewResponse = await res.json();
        if (json.error) {
          throw new Error(json.error);
        }
        setData(json);
        
        // Domyślnie zaznaczamy wszystkie z wysokim confidence
        const toSelect = new Set<string>();
        json.features.forEach(f => {
          if (f.mapping_confidence >= 0.90) {
            toSelect.add(f.feature_key);
          }
        });
        setSelectedFeatures(toSelect);
        
      } catch (err) {
        setError(err instanceof Error ? err.message : "Nieznany błąd");
      } finally {
        setLoading(false);
      }
    }
    loadPreview();
  }, [vehicleId, catalogId]);

  const toggleFeature = (key: string) => {
    setSelectedFeatures(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toggleAll = () => {
    if (!data) return;
    if (selectedFeatures.size === data.features.length) {
      setSelectedFeatures(new Set()); // deselect all
    } else {
      setSelectedFeatures(new Set(data.features.map(f => f.feature_key))); // select all
    }
  };

  const handleSave = async () => {
    if (!data || selectedFeatures.size === 0) return;
    setSaving(true);
    setError(null);
    
    try {
      const featuresToSave = data.features.filter(f => selectedFeatures.has(f.feature_key));
      
      const payload = {
        catalog_id: catalogId,
        features: featuresToSave
      };

      const res = await apiFetch(`/api/features/vehicle/${vehicleId}/add-selected-catalog-features`, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Błąd podczas zapisywania cech");
      }

      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd podczas zapisu");
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center p-4 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div>
            <h2 className="text-lg font-semibold text-slate-800">
              Podgląd funkcji: {catalogName}
            </h2>
            {data && (
              <p className="text-xs text-slate-500 mt-0.5">
                Dopasowany wariant: {data.matched_variant} (Pewność: {Math.round(data.confidence * 100)}%)
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 flex-1 overflow-y-auto bg-slate-50/50">
          {loading && (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin mb-4 text-indigo-500" />
              <p>Trwa analizowanie cech cennika...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 text-red-700 p-4 rounded-lg text-sm border border-red-200">
              {error}
            </div>
          )}

          {!loading && !error && data && data.features.length === 0 && (
            <div className="text-center py-12 text-slate-500">
              Nie udało się wyekstrahować żadnych dodatkowych cech z tego cennika.
            </div>
          )}

          {!loading && !error && data && data.features.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-slate-600">
                  Wybierz cechy, które chcesz skopiować z cennika do tego pojazdu.
                </p>
                <button
                  onClick={toggleAll}
                  className="text-xs font-medium text-indigo-600 hover:text-indigo-700"
                >
                  {selectedFeatures.size === data.features.length ? 'Odznacz wszystkie' : 'Zaznacz wszystkie'}
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {data.features.map(f => {
                  const isSelected = selectedFeatures.has(f.feature_key);
                  const isLowConfidence = f.mapping_confidence < 0.90;
                  
                  return (
                    <div
                      key={f.feature_key}
                      onClick={() => toggleFeature(f.feature_key)}
                      className={`
                        relative flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all
                        ${isSelected 
                          ? 'bg-indigo-50 border-indigo-200 shadow-sm' 
                          : 'bg-white border-slate-200 hover:border-indigo-100 hover:bg-slate-50'}
                      `}
                    >
                      <div className={`
                        flex-shrink-0 mt-0.5 w-5 h-5 rounded border flex items-center justify-center
                        ${isSelected ? 'bg-indigo-600 border-indigo-600' : 'bg-white border-slate-300'}
                      `}>
                        {isSelected && <Check className="w-3.5 h-3.5 text-white" />}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-medium ${isSelected ? 'text-indigo-900' : 'text-slate-700'}`}>
                          {f.feature_key}
                        </p>
                        <div className="flex flex-wrap gap-2 mt-1">
                          {f.value_bool !== null && (
                            <span className="text-xs bg-white text-slate-600 px-1.5 py-0.5 border rounded">
                              {f.value_bool ? 'Tak' : 'Nie'}
                            </span>
                          )}
                          {f.value_text !== null && (
                            <span className="text-xs bg-white text-slate-600 px-1.5 py-0.5 border rounded">
                              {f.value_text}
                            </span>
                          )}
                          {f.value_num !== null && (
                            <span className="text-xs bg-white text-slate-600 px-1.5 py-0.5 border rounded">
                              {f.value_num} {f.unit}
                            </span>
                          )}
                        </div>
                        {isLowConfidence && (
                          <p className="text-[10px] text-amber-600 mt-1.5 font-medium bg-amber-50 px-1.5 py-0.5 rounded inline-block">
                            Niska pewność dopasowania ({Math.round(f.mapping_confidence * 100)}%)
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
              
              {data.reasoning && (
                <div className="mt-6 p-4 bg-slate-100 rounded-lg text-xs justify-start text-slate-600 flex gap-2">
                   <div className="font-semibold text-slate-700">Uzasadnienie AI: </div> {data.reasoning}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 bg-white rounded-b-xl flex items-center justify-between">
          <p className="text-sm text-slate-500">
            Wybrano: <span className="font-bold text-slate-700">{selectedFeatures.size}</span> cech
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
              disabled={saving}
            >
              Anuluj
            </button>
            <button
              onClick={handleSave}
              disabled={saving || selectedFeatures.size === 0}
              className={`
                flex items-center gap-2 px-5 py-2 text-sm font-medium text-white rounded-lg shadow-sm transition-all
                ${saving || selectedFeatures.size === 0 
                  ? 'bg-indigo-300 cursor-not-allowed' 
                  : 'bg-indigo-600 hover:bg-indigo-700 hover:shadow'}
              `}
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Zapisywanie...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Dodaj cechy ({selectedFeatures.size})
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

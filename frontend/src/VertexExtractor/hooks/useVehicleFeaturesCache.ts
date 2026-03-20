import { apiClient } from '../../lib/apiClient';

export interface FeatureItem {
  feature_key: string;
  display_name: string;
  resolved_status: string;
  resolved_value_bool: boolean | null;
  resolved_value_text: string | null;
  resolved_value_num: number | null;
  confidence_score: number | null;
  category_name: string;
}

export interface SuggestedCatalog {
  catalog_id: string;
  score: number;
  display_name: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const featuresCache = new Map<string, { instantFeatures: FeatureItem[], data: any, suggestedCatalog: SuggestedCatalog | null }>();

const loadQueue: string[] = [];
let isQueueProcessing = false;

async function processQueue() {
  if (isQueueProcessing) return;
  isQueueProcessing = true;
  while (loadQueue.length > 0) {
    const vid = loadQueue.shift();
    if (vid && !featuresCache.has(vid)) {
      try {
         await fetchFeaturesForCache(vid);
      } catch (e) {
         console.warn("Background preload failed for", vid, e);
      }
      // Add a small delay between requests to not hammer the server
      await new Promise(r => setTimeout(r, 200));
    }
  }
  isQueueProcessing = false;
}

export function queuePreloadVehicleFeatures(vehicleId: string) {
  if (featuresCache.has(vehicleId)) return;
  if (!loadQueue.includes(vehicleId)) {
    loadQueue.push(vehicleId);
    processQueue();
  }
}

export async function fetchFeaturesForCache(vehicleId: string) {
    let instantFeatures: FeatureItem[] = [];
    let data: any = null;
    let cachedCatalog: SuggestedCatalog | null = null;
    
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const vehicleResp = await apiClient.fetch(`/api/kalkulator/pojazd/${vehicleId}`);
    if (vehicleResp.ok) {
        const vehicleData = await vehicleResp.json();
        const synthDataRaw = vehicleData.synthesis_data || {};
        const synthData = synthDataRaw.card_summary || {};
        
        if (synthDataRaw.suggested_catalog) {
            cachedCatalog = synthDataRaw.suggested_catalog;
        }
        
        const stdEq = (synthData.standard_equipment || []).map((name: string, i: number) => ({
          feature_key: `config_std_${name}_${i}`,
          display_name: name,
          resolved_status: "present_confirmed_primary",
          resolved_value_bool: true,
          resolved_value_text: null,
          resolved_value_num: null,
          confidence_score: 1.0,
          category_name: "⭐ Konfiguracja (PDF)"
        }));

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const paidEq = (synthData.paid_options || []).map((opt: any, i: number) => ({
          feature_key: `config_paid_${opt.name}_${i}`,
          display_name: opt.name,
          resolved_status: "present_confirmed_primary",
          resolved_value_bool: true,
          resolved_value_text: opt.price,
          resolved_value_num: null,
          confidence_score: 1.0,
          category_name: "⭐ Konfiguracja (PDF)"
        }));
        
        instantFeatures = [...stdEq, ...paidEq];
    }

    const response = await apiClient.fetch(`/api/features/vehicle/${vehicleId}/state`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    data = await response.json();
    
    featuresCache.set(vehicleId, { instantFeatures, data, suggestedCatalog: cachedCatalog });
    return featuresCache.get(vehicleId)!;
}

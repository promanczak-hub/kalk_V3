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
  feature_tier?: 'CORE' | 'EXTENDED' | 'EDGE' | null;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const featuresCache = new Map<string, { instantFeatures: FeatureItem[], data: any }>();

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
        console.warn(`[Cache] Preload failed for ${vid}, retrying once...`, e);
        // Wait 1s and retry once
        await new Promise((r) => setTimeout(r, 1000));
        try {
          await fetchFeaturesForCache(vid);
        } catch (e2) {
          console.error(`[Cache] Final failure for ${vid}:`, e2);
        }
      }
      // Increased delay to 500ms to avoid slamming the Granian/Uvicorn dev server on Windows
      await new Promise((r) => setTimeout(r, 500));
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
    let data: unknown = null;
    
    const vehicleResp = await apiClient.fetch(`/api/kalkulator/pojazd/${vehicleId}?lite=true`);
    if (vehicleResp.ok) {
        const vehicleData = await vehicleResp.json();
        const synthDataRaw = vehicleData.synthesis_data || {};
        const synthData = synthDataRaw.card_summary || {};
        
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

        // Dimension chips — clarified 2026-05-19: "cechy użytkowe" should cover
        // ALL vehicle features including masses/dimensions, not just paid options.
        // Reads card_summary.dimensions FIRST (filled by deterministic_normalize),
        // then falls back to digital_twin.dimensions (legacy/pre-V3 records).
        const dims = (
          (synthData.dimensions as Record<string, number | null> | undefined)
          ?? (synthDataRaw.digital_twin?.dimensions as Record<string, number | null> | undefined)
          ?? {}
        );
        const dimensionFeatures: FeatureItem[] = [];

        const pushDim = (key: string, label: string, value: number | null | undefined, unit: string) => {
          if (typeof value === "number" && value > 0) {
            dimensionFeatures.push({
              feature_key: `dim_${key}`,
              display_name: label,
              resolved_status: "present_confirmed_primary",
              resolved_value_bool: null,
              resolved_value_text: `${value} ${unit}`,
              resolved_value_num: null,
              confidence_score: 1.0,
              category_name: "Wymiary",
            });
          }
        };

        // Vehicle envelope (mm)
        pushDim("length_mm",     "Długość",      dims.length_mm,     "mm");
        pushDim("width_mm",      "Szerokość",    dims.width_mm,      "mm");
        pushDim("height_mm",     "Wysokość",     dims.height_mm,     "mm");
        pushDim("wheelbase_mm",  "Rozstaw osi",  dims.wheelbase_mm,  "mm");

        // Cargo bay (LCV/pickups)
        pushDim("cargo_length_mm", "Długość bagażnika",   dims.cargo_length_mm, "mm");
        pushDim("cargo_width_mm",  "Szerokość bagażnika", dims.cargo_width_mm,  "mm");
        pushDim("cargo_height_mm", "Wysokość bagażnika",  dims.cargo_height_mm, "mm");
        pushDim("cargo_volume_m3", "Pojemność bagażnika", dims.cargo_volume_m3, "m³");

        // Masses (kg)
        pushDim("payload_kg",              "Ładowność",     dims.payload_kg,              "kg");
        pushDim("curb_weight_kg",          "Masa własna",   dims.curb_weight_kg,          "kg");
        pushDim("gross_vehicle_weight_kg", "DMC",           dims.gross_vehicle_weight_kg, "kg");

        // Fuel tank
        pushDim("fuel_tank_capacity_l", "Zbiornik paliwa", dims.fuel_tank_capacity_l, "l");

        // Extended specs chips — purely informational data from the isolated
        // Flash pass (digital_twin.extended_specs): engine detail, transmission,
        // towing, chassis, WLTP cycles, tire labels, offer metadata.
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const ext = (synthDataRaw.digital_twin?.extended_specs ?? {}) as Record<string, any>;
        const extendedFeatures: FeatureItem[] = [];

        const pushSpec = (
          key: string,
          label: string,
          value: string | number | boolean | null | undefined,
          category: string,
          unit = "",
        ) => {
          if (value === null || value === undefined || value === "") return;
          const text =
            typeof value === "boolean"
              ? (value ? "Tak" : "Nie")
              : `${value}${unit ? " " + unit : ""}`;
          extendedFeatures.push({
            feature_key: `ext_${key}`,
            display_name: label,
            resolved_status: "present_confirmed_primary",
            resolved_value_bool: typeof value === "boolean" ? value : null,
            resolved_value_text: text,
            resolved_value_num: null,
            confidence_score: 1.0,
            category_name: category,
          });
        };

        const eng = ext.engine ?? {};
        pushSpec("eng_cyl",   "Liczba cylindrów",     eng.cylinders,            "Silnik");
        pushSpec("eng_torq",  "Moment obrotowy",      eng.max_torque_nm,        "Silnik", "Nm");
        pushSpec("eng_prpm",  "Obroty maks. mocy",    eng.max_power_rpm,        "Silnik", "obr./min");
        pushSpec("eng_trpm",  "Obroty maks. momentu", eng.max_torque_rpm,       "Silnik", "obr./min");
        pushSpec("eng_vmax",  "Prędkość maksymalna",  eng.top_speed_kmh,        "Silnik", "km/h");
        pushSpec("eng_acc",   "Przyspieszenie 0-100", eng.acceleration_0_100_s, "Silnik", "s");
        pushSpec("eng_emis",  "Norma emisji",         eng.emission_standard,    "Silnik");

        const trm = ext.transmission ?? {};
        pushSpec("trm_name",  "Skrzynia biegów",      trm.name,                 "Napęd");
        pushSpec("trm_gears", "Liczba biegów",        trm.gears,                "Napęd");
        pushSpec("trm_clutch","Sprzęgło",             trm.clutch,               "Napęd");

        const tow = ext.towing ?? {};
        pushSpec("tow_br",    "Przyczepa z hamulcem",  tow.trailer_braked_kg,   "Holowanie", "kg");
        pushSpec("tow_unbr",  "Przyczepa bez hamulca", tow.trailer_unbraked_kg, "Holowanie", "kg");
        pushSpec("tow_roof",  "Obciążenie dachu",      tow.roof_load_kg,        "Holowanie", "kg");
        pushSpec("tow_hitch", "Nacisk na hak",         tow.hitch_load_kg,       "Holowanie", "kg");

        const ch = ext.chassis ?? {};
        pushSpec("ch_turn",   "Średnica zawracania",  ch.turning_radius_m,      "Podwozie", "m");
        pushSpec("ch_front",  "Zawieszenie przednie", ch.front_suspension,      "Podwozie");
        pushSpec("ch_rear",   "Zawieszenie tylne",    ch.rear_suspension,       "Podwozie");

        const wltp = ext.wltp ?? {};
        pushSpec("wltp_low",  "WLTP cykl niski",        wltp.low,       "Zużycie WLTP", "l/100km");
        pushSpec("wltp_med",  "WLTP cykl średni",       wltp.medium,    "Zużycie WLTP", "l/100km");
        pushSpec("wltp_high", "WLTP cykl wysoki",       wltp.high,      "Zużycie WLTP", "l/100km");
        pushSpec("wltp_vh",   "WLTP cykl b. wysoki",    wltp.very_high, "Zużycie WLTP", "l/100km");
        pushSpec("wltp_comb", "WLTP cykl mieszany",     wltp.combined,  "Zużycie WLTP", "l/100km");

        pushSpec("model_year",   "Rok modelowy",      ext.model_year,        "Oferta");
        pushSpec("prod_year",    "Rok produkcji",     ext.production_year,   "Oferta");
        pushSpec("valid_until",  "Oferta ważna do",   ext.offer_valid_until, "Oferta");

        // Tire labels (EU 2020/740) — one chip per tire, informational
        const tires = Array.isArray(ext.tire_labels) ? ext.tire_labels : [];
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        tires.forEach((t: Record<string, any>, i: number) => {
          const parts = [t.manufacturer, t.name, t.size].filter(Boolean).join(" ");
          const label = parts || `Opona ${i + 1}`;
          const classes = [
            t.fuel_class ? `paliwo ${t.fuel_class}` : null,
            t.wet_grip_class ? `mokro ${t.wet_grip_class}` : null,
            t.noise_class ? `hałas ${t.noise_class}` : null,
            typeof t.noise_db === "number" ? `${t.noise_db} dB` : null,
          ].filter(Boolean).join(" · ");
          pushSpec(`tire_${i}`, label, classes || "—", "Opony (etykieta UE)");
        });

        instantFeatures = [...stdEq, ...paidEq, ...dimensionFeatures, ...extendedFeatures];
    }

    // Feature-state is supplementary (consumed by VehicleFeaturesCard). A failure here
    // must NOT discard the equipment already built from the lite fetch above, so it is
    // non-fatal — we still cache instantFeatures below.
    let response: Response | null = null;
    try {
        response = await apiClient.fetch(`/api/features/vehicle/${vehicleId}/state`);
    } catch (e) {
        console.warn(`[Cache] feature-state fetch failed for ${vehicleId}; caching equipment only.`, e);
    }
     
    if (response && response.ok) data = await response.json();
    
    featuresCache.set(vehicleId, { instantFeatures, data });
    return featuresCache.get(vehicleId)!;
}

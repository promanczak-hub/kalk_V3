import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface OfferVariant {
  duration_months: number | null;
  annual_mileage: number | null;
  monthly_price_net: number | null;
  found: boolean;
  variants_count?: number;
  tire_class?: string;
  service_type?: string;
  kalkulacja_id?: string;
}

/** Snapshot of the kalkulacja's pricing toggles + financing knobs at the
 *  moment the user added the item to the cart. Mirrors the backend's
 *  KalkulacjaSnapshotParams so <KalkulacjaParamsRow> can render the same
 *  context next to the price in every place the cart is displayed. */
export interface OfferItemKalkulacjaSnapshot {
  tire_class?: string | null;
  service_type?: string | null;
  discount_pct?: number | null;
  bank_margin_pct?: number | null;
  wibor_pct?: number | null;
  tires_included?: boolean | null;
  tire_buyback?: boolean | null;
  insurance_included?: boolean | null;
  replacement_car?: boolean | null;
  service_included?: boolean | null;
}

export interface OfferItem {
  id: string; // Unique combination of kalk_id_months_mileage
  brand: string;
  model: string;
  powertrain: string;
  vin_or_config: string;
  term: number;
  mileage: number;
  net_installment: number;
  contribution: number;
  margin_pct?: number;
  system_recommendation?: string; // e.g. "Low Monthly", "Best Value"
  calculation_data: unknown; // Raw JSON cell
  standard_equipment: string[];
  factory_options: string[];
  dealer_options: string[];
  variants?: OfferVariant[];
  // Per-cart-item editable fields (live only for this offer):
  notes?: string;
  overuse_fee?: number; // zł/km — picked from dropdown 0.10..0.80 step 0.01
  /** Frozen at add-to-cart time. The vehicle's current kalkulacja can change
   *  later (recalc, new pricing), but the offer keeps the params it was
   *  generated under so the printout matches what the customer was quoted. */
  kalkulacja_snapshot?: OfferItemKalkulacjaSnapshot;
}

export interface ClientData {
  companyName: string;
  nip: string;
  address: string;
  representative: string;
}

interface OfferCartState {
  items: OfferItem[];
  clientData: ClientData;
  addItem: (item: OfferItem) => void;
  addItems: (items: OfferItem[]) => void;
  removeItem: (id: string) => void;
  updateItem: (id: string, patch: Partial<OfferItem>) => void;
  clearCart: () => void;
  setClientData: (data: Partial<ClientData>) => void;
}

export const useOfferCartStore = create<OfferCartState>()(
  persist(
    (set) => ({
      items: [],
      clientData: {
        companyName: '',
        nip: '',
        address: '',
        representative: '',
      },
      addItem: (item) =>
        set((state) => {
          if (state.items.some((i) => i.id === item.id)) {
            return state;
          }
          return { items: [...state.items, item] };
        }),
      addItems: (newItems) =>
        set((state) => {
          const toAdd = newItems.filter(
            (ni) => !state.items.some((i) => i.id === ni.id)
          );
          if (toAdd.length === 0) return state;
          return { items: [...state.items, ...toAdd] };
        }),
      removeItem: (id) =>
        set((state) => ({
          items: state.items.filter((item) => item.id !== id),
        })),
      updateItem: (id, patch) =>
        set((state) => ({
          items: state.items.map((it) => (it.id === id ? { ...it, ...patch } : it)),
        })),
      clearCart: () =>
        set({
          items: [],
          clientData: {
            companyName: '',
            nip: '',
            address: '',
            representative: '',
          },
        }),
      setClientData: (data) =>
        set((state) => ({
          clientData: { ...state.clientData, ...data },
        })),
    }),
    {
      name: 'ltr-offer-cart-storage',
    }
  )
);

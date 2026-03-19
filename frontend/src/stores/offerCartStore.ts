import { create } from 'zustand';
import { persist } from 'zustand/middleware';

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
  system_recommendation?: string; // e.g. "Low Monthly", "Best Value"
  calculation_data: any; // Raw JSON cell
  standard_equipment: string[];
  factory_options: string[];
  dealer_options: string[];
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

import { beforeEach, describe, expect, it } from "vitest";
import { useOfferCartStore, type OfferItem } from "./offerCartStore";

const makeItem = (id: string, overrides: Partial<OfferItem> = {}): OfferItem => ({
  id,
  brand: "Skoda",
  model: "Octavia",
  powertrain: "1.5 TSI",
  vin_or_config: "config-1",
  term: 48,
  mileage: 80000,
  net_installment: 1500,
  contribution: 0,
  calculation_data: null,
  standard_equipment: [],
  factory_options: [],
  dealer_options: [],
  ...overrides,
});

const resetStore = () => {
  useOfferCartStore.setState({
    items: [],
    clientData: { companyName: "", nip: "", address: "", representative: "" },
  });
};

beforeEach(() => {
  resetStore();
});

describe("offerCartStore", () => {
  describe("addItem", () => {
    it("appends a new item", () => {
      useOfferCartStore.getState().addItem(makeItem("a"));
      expect(useOfferCartStore.getState().items).toHaveLength(1);
    });

    it("dedupes by id", () => {
      const item = makeItem("a");
      useOfferCartStore.getState().addItem(item);
      useOfferCartStore.getState().addItem({ ...item, net_installment: 9999 });
      expect(useOfferCartStore.getState().items).toHaveLength(1);
      expect(useOfferCartStore.getState().items[0].net_installment).toBe(1500);
    });
  });

  describe("addItems", () => {
    it("filters out duplicates already in cart", () => {
      useOfferCartStore.getState().addItem(makeItem("a"));
      useOfferCartStore.getState().addItems([makeItem("a"), makeItem("b"), makeItem("c")]);
      const ids = useOfferCartStore.getState().items.map((i) => i.id);
      expect(ids).toEqual(["a", "b", "c"]);
    });

    it("is a no-op when nothing is new", () => {
      useOfferCartStore.getState().addItem(makeItem("a"));
      const before = useOfferCartStore.getState().items;
      useOfferCartStore.getState().addItems([makeItem("a")]);
      expect(useOfferCartStore.getState().items).toBe(before);
    });
  });

  describe("removeItem", () => {
    it("removes by id", () => {
      useOfferCartStore.getState().addItems([makeItem("a"), makeItem("b")]);
      useOfferCartStore.getState().removeItem("a");
      expect(useOfferCartStore.getState().items.map((i) => i.id)).toEqual(["b"]);
    });
  });

  describe("updateItem", () => {
    it("patches only the matching item", () => {
      useOfferCartStore.getState().addItems([makeItem("a"), makeItem("b")]);
      useOfferCartStore.getState().updateItem("a", { notes: "VIP client" });
      const items = useOfferCartStore.getState().items;
      expect(items.find((i) => i.id === "a")?.notes).toBe("VIP client");
      expect(items.find((i) => i.id === "b")?.notes).toBeUndefined();
    });
  });

  describe("clearCart", () => {
    it("resets items and clientData", () => {
      useOfferCartStore.getState().addItem(makeItem("a"));
      useOfferCartStore.getState().setClientData({ companyName: "ACME" });
      useOfferCartStore.getState().clearCart();
      const { items, clientData } = useOfferCartStore.getState();
      expect(items).toEqual([]);
      expect(clientData).toEqual({
        companyName: "",
        nip: "",
        address: "",
        representative: "",
      });
    });
  });

  describe("setClientData", () => {
    it("merges partial updates", () => {
      useOfferCartStore.getState().setClientData({ companyName: "ACME" });
      useOfferCartStore.getState().setClientData({ nip: "1234567890" });
      expect(useOfferCartStore.getState().clientData).toEqual({
        companyName: "ACME",
        nip: "1234567890",
        address: "",
        representative: "",
      });
    });
  });
});

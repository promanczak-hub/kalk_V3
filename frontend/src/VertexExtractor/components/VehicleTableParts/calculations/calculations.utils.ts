export type NormalizedOption = {
  name: string;
  price_net: number;
  price_gross: number;
  no_discount: boolean;
  include_in_wr: boolean;
};

export function fmtPLN(val: number): string {
  return val.toLocaleString("pl-PL", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

export function parsePriceToNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (!value) return 0;
  
  let s = String(value).replace(/\s/g, "").replace(/[^\d,.-]/g, "");
  if (s.includes(".") && s.includes(",")) s = s.replace(/\./g, "");
  s = s.replace(",", ".");
  
  const parsed = parseFloat(s);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function mapPaidOption(
  row: Record<string, unknown>,
  index: number,
  defaultPriceDomain: string,
): NormalizedOption | null {
  const name = String(row.name || `Opcja ${index + 1}`);
  const rawPrice = row.price;
  const amount = parsePriceToNumber(rawPrice);
  if (amount <= 0) return null;

  const priceType = String(row.price_type || "").toLowerCase();
  const rawPriceString = typeof rawPrice === "string" ? rawPrice.toLowerCase() : "";
  const isBrutto =
    priceType.includes("brutto") ||
    rawPriceString.includes("brutto") ||
    defaultPriceDomain === "brutto";

  const priceNet = isBrutto ? amount / 1.23 : amount;
  const priceGross = isBrutto ? amount : amount * 1.23;

  return {
    name,
    price_net: Number(priceNet.toFixed(2)),
    price_gross: Number(priceGross.toFixed(2)),
    no_discount: Boolean(row.no_discount),
    include_in_wr: Boolean(row.include_in_wr),
  };
}

export function isFactoryCategory(category: unknown): boolean {
  const normalized = String(category || "").toLowerCase();
  return !normalized || normalized.includes("fabryczna");
}

export function extractOptionsFromPaidOptions(
  paidOptions: unknown,
  defaultPriceDomain?: string,
): { factory: NormalizedOption[]; service: NormalizedOption[] } {
  let rows: unknown[] = [];
  if (Array.isArray(paidOptions)) {
    rows = paidOptions;
  } else if (paidOptions && typeof paidOptions === "object") {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const poDict = paidOptions as any;
    if (Array.isArray(poDict.options)) {
      rows = poDict.options;
    } else if (Array.isArray(poDict.paid_options)) {
      rows = poDict.paid_options;
    }
  }

  const normalizedDomain = String(defaultPriceDomain || "").toLowerCase();
  const factory: NormalizedOption[] = [];
  const service: NormalizedOption[] = [];

  rows.forEach((rawRow, index) => {
    const row = (rawRow ?? {}) as Record<string, unknown>;
    const mapped = mapPaidOption(row, index, normalizedDomain);
    if (!mapped) return;

    if (isFactoryCategory(row.category)) {
      factory.push({ ...mapped, include_in_wr: false });
      return;
    }

    // Opcje serwisowe są zawsze nierabatowane; include_in_wr steruje WR.
    service.push({ ...mapped, no_discount: false });
  });

  return { factory, service };
}

import { cn } from "../../../lib/utils";

export const parsePriceToNumber = (priceStr?: string | null): number => {
  if (!priceStr || priceStr === "Brak") return 0;
  
  let str = priceStr.replace(/\s+/g, "").replace(/[^\d.,-]/g, "");
  if (!str) return 0;

  const hasComma = str.includes(",");
  const hasDot = str.includes(".");
  
  if (hasComma && hasDot) {
    if (str.lastIndexOf(",") > str.lastIndexOf(".")) {
      str = str.replace(/\./g, "").replace(",", ".");
    } else {
      str = str.replace(/,/g, "");
    }
  } else if (hasComma) {
    const parts = str.split(",");
    if (parts.length === 2 && parts[1].length === 3) {
      str = str.replace(",", "");
    } else {
      str = str.replace(",", ".");
    }
  } else if (hasDot) {
    const parts = str.split(".");
    if (parts[parts.length - 1].length === 3) {
      str = str.replace(/\./g, "");
    }
  }
  
  const num = parseFloat(str);
  return isNaN(num) ? 0 : num;
};

export function PriceDualFormat({
  priceStr,
  align = "right",
  className = "",
  inline = false,
}: {
  priceStr?: string | null;
  align?: "left" | "center" | "right";
  className?: string;
  inline?: boolean;
}) {
  if (!priceStr || priceStr === "Brak") {
    return <span className="text-slate-400 font-normal text-sm">Brak</span>;
  }

  const cleaned = priceStr.toLowerCase();
  const value = parsePriceToNumber(priceStr);
  if (value === 0) return <span>{priceStr}</span>;

  const formatCurrency = (val: number) =>
    val
      .toLocaleString("pl-PL", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
      })
      .replace(",", ".") + " PLN";

  // Jeśli nie określono, domyślnie brutto
  const isNetto = cleaned.includes("netto");
  const netto = isNetto ? value : value / 1.23;
  const brutto = isNetto ? value * 1.23 : value;

  if (inline) {
    return (
       <span className={className}>
         {formatCurrency(brutto)} <span className="text-[0.9em]">brutto</span> /{" "}
         <span className="opacity-60">{formatCurrency(netto)} <span className="text-[0.9em]">netto</span></span>
       </span>
    );
  }

  const alignClass =
    align === "left"
      ? "items-start"
      : align === "center"
      ? "items-center"
      : "items-end";

  return (
    <div className={cn("flex flex-col", alignClass, className)}>
      <span className="flex items-baseline gap-1">
        {formatCurrency(brutto)}
        <span className="text-[0.7em] font-medium opacity-70 uppercase tracking-wider">
          brutto
        </span>
      </span>
      <span className="text-[0.65em] opacity-60 font-semibold leading-none mt-1 uppercase tracking-wider">
        {formatCurrency(netto)} netto
      </span>
    </div>
  );
}

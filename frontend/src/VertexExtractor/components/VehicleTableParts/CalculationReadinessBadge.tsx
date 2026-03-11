import { useMemo } from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { cn } from "../../../lib/utils";
import type { FleetVehicleView } from "../../types";

/**
 * Readiness Badge — wyświetla 🟢 / 🔴 z listą brakujących danych.
 * Zamontować w nagłówku sekcji Parametry Kalkulacji.
 *
 * Reguła biznesowa: kalkulacja precyzyjna jest NIEMOŻLIWA bez
 * pełnych danych. Żadnych fallbacków ani mocków.
 */

interface ReadinessCheck {
  label: string;
  ok: boolean;
  detail?: string;
}

interface CalculationReadinessBadgeProps {
  catalogBasePriceNet: number;
  rimDiameter: number | null;
  vehicle: FleetVehicleView;
  paramPreview?: {
    service: { found: boolean };
    tires: { found: boolean };
    vintage: { found: boolean };
    color: { found: boolean };
    replacement_car: { found: boolean };
  } | null;
  includeServicing: boolean;
  replacementCar: boolean;
}

export function CalculationReadinessBadge({
  catalogBasePriceNet,
  rimDiameter,
  vehicle,
  paramPreview,
  includeServicing,
  replacementCar,
}: CalculationReadinessBadgeProps) {
  const checks = useMemo<ReadinessCheck[]>(() => {
    const list: ReadinessCheck[] = [];

    // 1. Cena bazowa
    list.push({
      label: "Cena bazowa netto",
      ok: catalogBasePriceNet > 0,
      detail: catalogBasePriceNet > 0
        ? `${catalogBasePriceNet.toLocaleString("pl-PL")} PLN`
        : "Brak — wpisz lub sprawdź AI",
    });

    // 2. Klasa SAMAR — jedno źródło prawdy: mapped_ai_data.samar_category
    const samarCategory =
      (vehicle.synthesis_data?.mapped_ai_data as Record<string, unknown> | undefined)
        ?.samar_category as string | undefined;
    const hasSamar = !!samarCategory;
    list.push({
      label: "Klasa SAMAR",
      ok: hasSamar,
      detail: hasSamar
        ? samarCategory
        : "Brak — wymagana klasyfikacja SAMAR",
    });

    // 3. Średnica felgi
    list.push({
      label: "Średnica felgi",
      ok: rimDiameter !== null && rimDiameter > 0,
      detail: rimDiameter ? `${rimDiameter}"` : "Brak — wymagane do kosztów opon",
    });

    // 4. Stawka serwisowa (jeśli serwis włączony)
    if (includeServicing) {
      list.push({
        label: "Stawka serwisowa",
        ok: paramPreview?.service?.found ?? false,
        detail: paramPreview?.service?.found
          ? "Znaleziono w DB"
          : "Brak stawki — sprawdź samar_service_costs",
      });
    }

    // 5. Cena opon (z tabel)
    list.push({
      label: "Cena opon",
      ok: paramPreview?.tires?.found ?? false,
      detail: paramPreview?.tires?.found
        ? "Znaleziono w DB"
        : "Brak ceny w koszty_opon dla wybranej klasy/średnicy",
    });

    // 6. Samochód zastępczy (jeśli włączony)
    if (replacementCar) {
      list.push({
        label: "Samochód zastępczy",
        ok: paramPreview?.replacement_car?.found ?? false,
        detail: paramPreview?.replacement_car?.found
          ? "Znaleziono stawkę"
          : "Brak stawki — sprawdź replacement_car_rates",
      });
    }

    // 7. Stawki ubezpieczeniowe (wymagana klasa SAMAR → ltr_admin_ubezpieczenia)
    list.push({
      label: "Stawki ubezpieczeniowe",
      ok: hasSamar,
      detail: hasSamar
        ? "Klasa SAMAR przypisana → stawki AC/OC dostępne"
        : "Brak klasy SAMAR — niemożliwe pobranie stawek AC/OC",
    });

    return list;
  }, [catalogBasePriceNet, rimDiameter, vehicle, paramPreview, includeServicing, replacementCar]);

  const allOk = checks.every((c) => c.ok);
  const missingCount = checks.filter((c) => !c.ok).length;

  return (
    <div className="relative group">
      {/* Badge */}
      <div
        className={cn(
          "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold cursor-pointer transition-all",
          allOk
            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
            : "bg-red-50 text-red-700 border border-red-200 animate-pulse"
        )}
      >
        {allOk ? (
          <>
            <CheckCircle2 size={14} />
            Gotowe do kalkulacji
          </>
        ) : (
          <>
            <AlertTriangle size={14} />
            Brakuje {missingCount} {missingCount === 1 ? "parametru" : "parametrów"}
          </>
        )}
      </div>

      {/* Tooltip — lista checków */}
      <div className="absolute z-50 bottom-full left-0 mb-2 w-80 bg-white rounded-lg shadow-xl border border-slate-200 p-3 hidden group-hover:block">
        <div className="text-xs font-bold text-slate-700 mb-2 uppercase tracking-wider">
          Pre-analiza danych kalkulacji
        </div>
        <div className="space-y-1.5">
          {checks.map((check) => (
            <div key={check.label} className="flex items-start gap-2">
              <span className={cn("mt-0.5 shrink-0", check.ok ? "text-emerald-500" : "text-red-500")}>
                {check.ok ? "✓" : "✗"}
              </span>
              <div className="min-w-0">
                <div className={cn("text-xs font-semibold", check.ok ? "text-slate-700" : "text-red-700")}>
                  {check.label}
                </div>
                {check.detail && (
                  <div className="text-[10px] text-slate-400 truncate">{check.detail}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

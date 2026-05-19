import { Tooltip } from "@mui/material";
import { Wrench, Settings, Shield, CarFront, Tag, Package, type LucideIcon } from "lucide-react";
import { cn } from "../../../lib/utils";
import type { TogglesSummary } from "./VehicleCalculationsList";

interface ConfigDotStripProps {
  toggles?: TogglesSummary | null;
  optionsCount: number;
  discountPct: number | null;
}

type SlotState = "on" | "off" | "loading";

interface SlotProps {
  icon: LucideIcon;
  state: SlotState;
  ariaLabel: string;
  tooltipPrimary: string;
  badge?: string;
}

function Slot({ icon: Icon, state, ariaLabel, tooltipPrimary, badge }: SlotProps) {
  const iconColor =
    state === "on"
      ? "text-emerald-500"
      : state === "loading"
        ? "text-slate-200 animate-pulse"
        : "text-slate-300";

  return (
    <Tooltip title={tooltipPrimary} arrow placement="top" enterDelay={150}>
      <button
        type="button"
        tabIndex={0}
        aria-label={ariaLabel}
        className="inline-flex flex-col items-center justify-center w-7 h-7 cursor-help focus:outline-none focus:ring-1 focus:ring-blue-400 rounded"
        onClick={(e) => e.stopPropagation()}
      >
        <Icon className={cn("w-3.5 h-3.5", iconColor)} />
        {badge && (
          <span className="text-[8px] font-bold text-emerald-700 leading-none mt-0.5 tabular-nums">
            {badge}
          </span>
        )}
      </button>
    </Tooltip>
  );
}

/** Pasek 6 stałych slotów — Serwis / Opony / Ubezpieczenie / Auto zastępcze / Rabat / Opcje.
 *  Każdy slot w stałej pozycji, kolorowa ikonka = ON, szara = OFF, pulsująca = brak danych.
 *  Hover/focus → tooltip z pełnym opisem. */
export function ConfigDotStrip({ toggles, optionsCount, discountPct }: ConfigDotStripProps) {
  const loading = toggles == null;
  const toState = (v: boolean | undefined): SlotState =>
    loading ? "loading" : v ? "on" : "off";

  const discountState: SlotState = loading
    ? "loading"
    : discountPct != null && discountPct > 0
      ? "on"
      : "off";
  const optionsState: SlotState = loading
    ? "loading"
    : optionsCount > 0
      ? "on"
      : "off";

  return (
    <div className="flex items-center gap-1.5 h-full">
      <Slot
        icon={Wrench}
        state={toState(toggles?.include_servicing)}
        ariaLabel={`Serwis: ${toggles?.include_servicing ? "włączony" : "wyłączony"}`}
        tooltipPrimary={toggles?.include_servicing ? "Serwis: włączony" : "Serwis: wyłączony"}
      />
      <Slot
        icon={Settings}
        state={toState(toggles?.z_oponami)}
        ariaLabel={`Opony: ${toggles?.z_oponami ? "w cenie" : "poza ceną"}`}
        tooltipPrimary={toggles?.z_oponami ? "Opony: w cenie" : "Opony: poza ceną"}
      />
      <Slot
        icon={Shield}
        state={toState(toggles?.express_pays_insurance)}
        ariaLabel={`Ubezpieczenie: ${toggles?.express_pays_insurance ? "w cenie" : "poza ceną"}`}
        tooltipPrimary={
          toggles?.express_pays_insurance ? "Ubezpieczenie: w cenie" : "Ubezpieczenie: poza ceną"
        }
      />
      <Slot
        icon={CarFront}
        state={toState(toggles?.replacement_car)}
        ariaLabel={`Auto zastępcze: ${toggles?.replacement_car ? "tak" : "nie"}`}
        tooltipPrimary={
          toggles?.replacement_car ? "Auto zastępcze: tak" : "Auto zastępcze: nie"
        }
      />
      <Slot
        icon={Tag}
        state={discountState}
        ariaLabel={
          discountState === "on" ? `Rabat: -${discountPct}%` : "Brak rabatu"
        }
        tooltipPrimary={
          discountState === "on" ? `Rabat: -${discountPct}%` : "Brak rabatu"
        }
        badge={discountState === "on" ? `-${discountPct}%` : undefined}
      />
      <Slot
        icon={Package}
        state={optionsState}
        ariaLabel={
          optionsState === "on"
            ? `Opcje: ${optionsCount} dodatków`
            : "Brak opcji"
        }
        tooltipPrimary={
          optionsState === "on"
            ? `Opcje: ${optionsCount} dodatków`
            : "Brak opcji"
        }
        badge={optionsState === "on" ? String(optionsCount) : undefined}
      />
    </div>
  );
}

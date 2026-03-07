import type { MarginTier, MiniMatrixCell } from "./decision-center.types";

// ── Margin Tier System (min. yellow = 8%) ────────────────────────────────────

export function getMarginTier(pct: number): MarginTier {
  if (pct < 0) {
    return {
      label: "Ujemna",
      heatColor: "#ef4444",
      heatBg: "rgba(239,68,68,0.15)",
      textColor: "text-red-700",
      borderColor: "border-red-400",
      badgeBg: "bg-red-100",
      badgeText: "text-red-800",
    };
  }
  if (pct < 8) {
    return {
      label: "Poniżej min.",
      heatColor: "#f97316",
      heatBg: "rgba(249,115,22,0.12)",
      textColor: "text-orange-700",
      borderColor: "border-orange-400",
      badgeBg: "bg-orange-100",
      badgeText: "text-orange-800",
    };
  }
  if (pct < 12) {
    return {
      label: "Minimalna",
      heatColor: "#eab308",
      heatBg: "rgba(234,179,8,0.12)",
      textColor: "text-yellow-700",
      borderColor: "border-yellow-400",
      badgeBg: "bg-yellow-100",
      badgeText: "text-yellow-800",
    };
  }
  if (pct < 15) {
    return {
      label: "Dobra",
      heatColor: "#84cc16",
      heatBg: "rgba(132,204,22,0.12)",
      textColor: "text-lime-700",
      borderColor: "border-lime-400",
      badgeBg: "bg-lime-100",
      badgeText: "text-lime-800",
    };
  }
  if (pct < 20) {
    return {
      label: "Bardzo dobra",
      heatColor: "#22c55e",
      heatBg: "rgba(34,197,94,0.12)",
      textColor: "text-emerald-700",
      borderColor: "border-emerald-400",
      badgeBg: "bg-emerald-100",
      badgeText: "text-emerald-800",
    };
  }
  return {
    label: "Wysoka",
    heatColor: "#06b6d4",
    heatBg: "rgba(6,182,212,0.10)",
    textColor: "text-cyan-700",
    borderColor: "border-cyan-400",
    badgeBg: "bg-cyan-100",
    badgeText: "text-cyan-800",
  };
}

// ── Formatters ───────────────────────────────────────────────────────────────

export function fmtPLN(val: number): string {
  return val.toLocaleString("pl-PL", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

export function fmtPLN2(val: number): string {
  return val.toLocaleString("pl-PL", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function fmtKm(km: number): string {
  if (km >= 1000) return `${(km / 1000).toFixed(0)}k`;
  return `${km}`;
}

// ── KPI helpers ──────────────────────────────────────────────────────────────

export function findBestCell(cells: MiniMatrixCell[]): MiniMatrixCell | null {
  if (cells.length === 0) return null;
  // Best = highest margin % among viable (positive) options
  const viable = cells.filter((c) => c.marza_na_kontrakcie_pct > 0);
  if (viable.length === 0) return cells[0];

  // Score: weighted balance of margin quality and price attractiveness
  return viable.reduce((best, c) => {
    const bestScore = best.marza_na_kontrakcie_pct * 0.6 + (1 / best.price_net) * 10000 * 0.4;
    const cScore = c.marza_na_kontrakcie_pct * 0.6 + (1 / c.price_net) * 10000 * 0.4;
    return cScore > bestScore ? c : best;
  });
}

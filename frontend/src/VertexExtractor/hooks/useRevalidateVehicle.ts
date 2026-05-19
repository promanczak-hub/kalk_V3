/**
 * useRevalidateVehicle — shared hook used by every "Zapisz zmiany" handler
 * across sections (VehicleSummaryCard, VehicleEquipmentCard, VehicleServiceOptionsCard,
 * DiscountAuditCard, VehicleFinancialOptions, VehicleFeaturesCrud).
 *
 * After persisting field changes, call `revalidate(vehicleId)` to:
 *   1. Re-run validator + HITL review heuristic on the backend
 *   2. Flip verification_status to "completed" if no blocking issues remain
 *   3. Show toast feedback to the user (✓ Zweryfikowano / ⚠ Nadal wymaga)
 *
 * Idempotent — safe to call after every save.
 */
import { useState } from "react";
import { apiClient } from "../../lib/apiClient";

export interface RevalidateResponse {
  vehicle_id: string;
  verification_status_before: string;
  verification_status: string;
  needs_review: boolean;
  reasons: string[];
  changed: boolean;
}

export interface RevalidateState {
  loading: boolean;
  lastResult: RevalidateResponse | null;
  error: string | null;
}

export function useRevalidateVehicle() {
  const [state, setState] = useState<RevalidateState>({
    loading: false,
    lastResult: null,
    error: null,
  });

  const revalidate = async (vehicleId: string): Promise<RevalidateResponse | null> => {
    setState({ loading: true, lastResult: null, error: null });
    try {
      const result = await apiClient.post<RevalidateResponse>(
        `/api/extract/revalidate/${vehicleId}`,
      );
      setState({ loading: false, lastResult: result, error: null });
      return result;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setState({ loading: false, lastResult: null, error: msg });
      return null;
    }
  };

  return {
    ...state,
    revalidate,
  };
}

/**
 * Plain function variant — for save handlers that don't want React state
 * management. Returns the response or null on error. Logs to console.
 *
 * Use when the parent component already has a refresh callback and just
 * wants to trigger backend re-check + maybe show a toast.
 */
export async function revalidateVehicleQuiet(
  vehicleId: string,
): Promise<RevalidateResponse | null> {
  try {
    return await apiClient.post<RevalidateResponse>(
      `/api/extract/revalidate/${vehicleId}`,
    );
  } catch (e) {
    console.warn("[revalidate] failed:", e);
    return null;
  }
}

/**
 * Build a human-readable toast message from a revalidate response.
 * Returns null when nothing changed (no toast needed).
 */
export function buildRevalidateToast(
  result: RevalidateResponse | null,
): { severity: "success" | "warning" | "info"; message: string } | null {
  if (!result) return null;
  if (!result.changed) {
    // Status didn't flip — could be already correct or still needs review
    if (result.needs_review) {
      return null; // status stayed needs_review, no need to surprise the user
    }
    return null; // already completed, no message needed
  }
  // Status changed
  if (result.verification_status === "completed") {
    return {
      severity: "success",
      message: "✓ Pojazd zweryfikowany — wszystkie kontrole zaliczone",
    };
  }
  if (result.verification_status === "needs_review") {
    const top = result.reasons.slice(0, 3).join(", ");
    return {
      severity: "warning",
      message: `⚠ Nadal wymaga weryfikacji: ${top}${result.reasons.length > 3 ? "…" : ""}`,
    };
  }
  return {
    severity: "info",
    message: `Status: ${result.verification_status}`,
  };
}

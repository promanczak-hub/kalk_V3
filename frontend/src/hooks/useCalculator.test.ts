import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import axios from "axios";

vi.mock("axios");

import { useCalculator } from "./useCalculator";

const mockedAxios = vi.mocked(axios);

beforeEach(() => {
  // Default: fetchSettings on mount returns minimal control_center payload
  mockedAxios.get.mockResolvedValue({
    data: {
      vat_rate: 23,
      default_wibor: 5,
      bank_spread: 2,
    },
  });
  mockedAxios.post.mockResolvedValue({ data: { total_rent: 0, steps: [], summary: undefined } });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useCalculator — state updates", () => {
  it("starts with sensible defaults", () => {
    const { result } = renderHook(() => useCalculator());
    expect(result.current.vehicle.duration_months).toBe(48);
    expect(result.current.vehicle.annual_mileage).toBe(20000);
    expect(result.current.vehicle.has_tires).toBe(true);
    expect(result.current.factoryOptions).toEqual([]);
    expect(result.current.serviceOptions).toEqual([]);
    expect(result.current.calculationResult).toBeNull();
    expect(result.current.activeStep).toBe(0);
  });

  it("handleUpdate sets the named field", () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.handleUpdate("brand", "Skoda"));
    expect(result.current.vehicle.brand).toBe("Skoda");
  });

  it("updateVehicle merges a partial patch", () => {
    const { result } = renderHook(() => useCalculator());
    act(() =>
      result.current.updateVehicle({ brand: "BMW", model: "X3", trim_level: "M Sport" })
    );
    expect(result.current.vehicle.brand).toBe("BMW");
    expect(result.current.vehicle.model).toBe("X3");
    expect(result.current.vehicle.trim_level).toBe("M Sport");
    // unchanged
    expect(result.current.vehicle.duration_months).toBe(48);
  });
});

describe("useCalculator — net/gross conversion", () => {
  it("handleUpdateNetto sets net + gross using vat_rate (default 0.23)", () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.handleUpdateNetto(100000));
    expect(result.current.vehicle.base_price_net).toBe(100000);
    expect(result.current.vehicle.base_price_gross).toBeCloseTo(123000, 2);
  });

  it("handleUpdateBrutto sets gross + net derived back from gross", () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.handleUpdateBrutto(123000));
    expect(result.current.vehicle.base_price_gross).toBe(123000);
    expect(result.current.vehicle.base_price_net).toBeCloseTo(100000, 2);
  });
});

describe("useCalculator — discount handling", () => {
  it("handleChangeTypRabatu flips discount_type", () => {
    const { result } = renderHook(() => useCalculator());
    expect(result.current.vehicle.discount_type).toBe("Procentowo");
    act(() => result.current.handleChangeTypRabatu("Kwotowo"));
    expect(result.current.vehicle.discount_type).toBe("Kwotowo");
  });

  it("handleUpdateRabat with Procentowo stores discount_pct as decimal (value/100)", () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.handleUpdateRabat("Procentowo", 15));
    expect(result.current.vehicle.discount_pct).toBe(0.15);
  });

  it("handleUpdateRabat with Kwotowo stores discount_amount_net verbatim", () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.handleUpdateRabat("Kwotowo", 5000));
    expect(result.current.vehicle.discount_amount_net).toBe(5000);
  });
});

describe("useCalculator — factory + service options", () => {
  it("addFactoryOption appends with default fields", () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.addFactoryOption());
    expect(result.current.factoryOptions).toHaveLength(1);
    expect(result.current.factoryOptions[0].name).toBe("Nowa opcja fabryczna");
    expect(result.current.factoryOptions[0].price_net).toBe(0);
  });

  it("removeFactoryOption drops the matched id", () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.addFactoryOption());
    const targetId = result.current.factoryOptions[0].id;
    act(() => result.current.removeFactoryOption(targetId));
    expect(result.current.factoryOptions).toHaveLength(0);
  });

  it("addServiceOption + removeServiceOption mirror factory behavior", () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.addServiceOption());
    expect(result.current.serviceOptions).toHaveLength(1);
    expect(result.current.serviceOptions[0].name).toBe("Nowa opcja serwisowa");
    const targetId = result.current.serviceOptions[0].id;
    act(() => result.current.removeServiceOption(targetId));
    expect(result.current.serviceOptions).toHaveLength(0);
  });
});

describe("useCalculator — stepper + accordion", () => {
  it("handleNext / handleBack advance + retract activeStep", () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.handleNext());
    expect(result.current.activeStep).toBe(1);
    act(() => result.current.handleNext());
    expect(result.current.activeStep).toBe(2);
    act(() => result.current.handleBack());
    expect(result.current.activeStep).toBe(1);
  });

  it("handleReset returns activeStep to 0 + clears results", () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.handleNext());
    act(() => result.current.handleUpdate("brand", "Toyota"));
    act(() => result.current.handleReset());
    expect(result.current.activeStep).toBe(0);
    expect(result.current.vehicle.brand).toBe("");
    expect(result.current.calculationResult).toBeNull();
    expect(result.current.steps).toEqual([]);
  });

  it("handleAccordionChange sets the open panel name when isExpanded=true", () => {
    const { result } = renderHook(() => useCalculator());
    const fakeEvent = {} as unknown as React.SyntheticEvent;
    act(() => result.current.handleAccordionChange("panel3")(fakeEvent, true));
    expect(result.current.expandedPanel).toBe("panel3");
    act(() => result.current.handleAccordionChange("panel3")(fakeEvent, false));
    expect(result.current.expandedPanel).toBe(false);
  });
});

describe("useCalculator — async behavior", () => {
  it("fetchSettings on mount applies vat_rate / wibor / bank_spread as decimals", async () => {
    const { result } = renderHook(() => useCalculator());
    await waitFor(() => {
      expect(result.current.vehicle.vat_rate).toBeCloseTo(0.23, 4);
    });
    expect(result.current.vehicle.wibor_pct).toBeCloseTo(0.05, 4);
    expect(result.current.vehicle.financial_margin_pct).toBeCloseTo(0.02, 4);
  });

  it("fetchSettings tolerates fetch failure (logs only, no crash)", async () => {
    mockedAxios.get.mockRejectedValueOnce(new Error("network down"));
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const { result } = renderHook(() => useCalculator());
    // No crash; state stays at INITIAL_DATA defaults
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled();
    });
    expect(result.current.vehicle.vat_rate).toBe(0.23); // INITIAL_DATA default
  });

  it("calculate posts payload and stores result + steps", async () => {
    mockedAxios.post.mockResolvedValueOnce({
      data: {
        total_rent: 1234.56,
        steps: [{ krok: "Stawka", wynik: 1234.56 }],
        summary: { base_price_net: 100000, total_discount_net: 0, final_price_net: 100000 },
      },
    });
    const { result } = renderHook(() => useCalculator());
    await act(async () => {
      await result.current.calculate();
    });
    expect(result.current.calculationResult?.total_rent).toBe(1234.56);
    expect(result.current.steps).toHaveLength(1);
    expect(result.current.steps[0].krok).toBe("Stawka");
    expect(result.current.isCalculating).toBe(false);
  });

  it("calculate flips isCalculating off even on axios failure", async () => {
    mockedAxios.post.mockRejectedValueOnce(new Error("backend down"));
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const { result } = renderHook(() => useCalculator());
    await act(async () => {
      await result.current.calculate();
    });
    expect(result.current.isCalculating).toBe(false);
    expect(consoleSpy).toHaveBeenCalled();
  });

  it("calculate sends derived fields (samar_category, engine_name, body_type_name, power_hp) in payload", async () => {
    const { result } = renderHook(() => useCalculator());
    act(() =>
      result.current.updateVehicle({
        samar_class: "Klasa 10",
        fuel_type: "Benzyna",
        body_type: "SUV",
        engine_power_hp: "150",
      })
    );
    await act(async () => {
      await result.current.calculate();
    });
    const postedPayload = mockedAxios.post.mock.calls[0][1] as Record<string, unknown>;
    expect(postedPayload.samar_category).toBe("Klasa 10");
    expect(postedPayload.engine_name).toBe("Benzyna");
    expect(postedPayload.body_type_name).toBe("SUV");
    expect(postedPayload.power_hp).toBe(150);
  });
});

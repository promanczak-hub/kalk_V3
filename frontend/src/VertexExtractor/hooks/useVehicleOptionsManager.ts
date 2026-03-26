import { useState, useEffect, useMemo } from "react";
import { supabase } from "../../lib/supabaseClient";
import { apiClient } from '../../lib/apiClient';
import type { FleetVehicleView, ModificationEffect, HomologationResponse } from "../../types";
import { parsePriceToNumber } from "../components/VehicleTableParts/PriceDualFormat";

export function useVehicleOptionsManager(vehicle: FleetVehicleView, onRefresh: () => void) {
  // Determine price domain from deterministic backend detection
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const priceDomain: string = ((vehicle.synthesis_data as any)?.card_summary?._price_domain) || "unknown";

  /** Convert a parsed price to netto, respecting the option's price_type or global domain. */
  const toNettoAware = (rawPrice: number, priceStr?: string, optPriceType?: string): number => {
    if (rawPrice === 0) return 0;
    // Priority: option-level price_type > detected string label > global domain
    const type = optPriceType && optPriceType !== "unknown"
      ? optPriceType
      : priceStr?.toLowerCase().includes("brutto")
        ? "brutto"
        : priceStr?.toLowerCase().includes("netto")
          ? "netto"
          : priceDomain;
    return type === "brutto" ? Math.round((rawPrice / 1.23) * 100) / 100 : rawPrice;
  };

  // Local state for CRUD operations on Service Options
  const initialServiceOptions = useMemo(() => {
    return vehicle.paid_options?.filter(
      (o) => o.category && !o.category.includes("Fabryczna")
    ).map(o => ({
       id: crypto.randomUUID(),
       name: o.name,
       price_net: o.price ? toNettoAware(parsePriceToNumber(o.price), o.price, (o as any).price_type) : 0,
       category: o.category || "Opcja Serwisowa",
       // @ts-expect-error - compatibility with older data model
       include_in_wr: o.include_in_wr || false
    })) || [];
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicle.paid_options, priceDomain]);

  const initialFactoryOptions = useMemo(() => {
    const opts = vehicle.paid_options?.filter(
      (o) => o.category?.includes("Fabryczna") || !o.category
    ).map(o => ({
       id: crypto.randomUUID(),
       name: o.name,
       price_net: o.price ? toNettoAware(parsePriceToNumber(o.price), o.price, (o as any).price_type) : 0,
       category: o.category || "Fabryczna",
       no_discount: (o as any).no_discount === true
    })) || [];

    if (vehicle.exterior_color && vehicle.exterior_color !== "Brak") {
      const normalizeColor = (s: string) =>
        s.toLowerCase()
          .replace(/^(lakier|kolor|color|paint):\s*/, "")
          .replace(/\s*\([^)]*\).*/, "")
          .trim();

      const normalizedExterior = normalizeColor(vehicle.exterior_color);
      const isAlreadyAdded = opts.some((opt: any) => {
        const normalizedOpt = normalizeColor(opt.name);
        return (
          normalizedOpt.includes(normalizedExterior) ||
          normalizedExterior.includes(normalizedOpt) ||
          opt.name.toLowerCase().includes("lakier")
        );
      });

      if (!isAlreadyAdded) {
        let name = `Lakier: ${vehicle.exterior_color}`;
        let priceNet = 0;
        const match =
          vehicle.exterior_color.match(
            /\((?:dopłata\s*)?([\d\s,.]+\s*(?:PLN|zł|pln|ZŁ).*?)\)/i,
          ) ||
          vehicle.exterior_color.match(/-\s*([\d\s,.]+\s*(?:PLN|zł|pln|ZŁ).*?)/i) ||
          vehicle.exterior_color.match(/(\d[\d\s]*\s*(?:PLN|zł|pln|ZŁ))/i);

        if (match) {
          const priceStr = match[1] || match[0];
          priceNet = toNettoAware(parsePriceToNumber(priceStr), priceStr);
          name = `Lakier: ${vehicle.exterior_color
            .replace(match[0], "")
            .replace(/\(\s*\)/, "")
            .trim()}`;
        }
        opts.unshift({ id: crypto.randomUUID(), name, price_net: priceNet, category: "Fabryczna", no_discount: false });
      }
    }
    return opts;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicle.paid_options, vehicle.exterior_color, priceDomain]);

   const [customServiceOptions, setCustomServiceOptions] = useState<{id: string, name: string, price_net: number, category: string, effects?: ModificationEffect, include_in_wr?: boolean}[]>([]);
   const [customFactoryOptions, setCustomFactoryOptions] = useState<{id: string, name: string, price_net: number, category: string, no_discount: boolean, effects?: ModificationEffect}[]>([]);
  
  // Set initial state only once or when vehicle completely changes
  useEffect(() => {
     setCustomServiceOptions(initialServiceOptions);
     setCustomFactoryOptions(initialFactoryOptions);
  }, [initialServiceOptions, initialFactoryOptions]);

  const handleUpdateServiceOptionName = (id: string, newName: string) => {
    setCustomServiceOptions(prev => prev.map(opt => opt.id === id ? { ...opt, name: newName } : opt));
  };

  const handleUpdateServiceOptionPrice = (id: string, newPrice: number) => {
    setCustomServiceOptions(prev => prev.map(opt => opt.id === id ? { ...opt, price_net: newPrice } : opt));
  };

  const handleUpdateServiceOptionIncludeInWr = (id: string, include: boolean) => {
    setCustomServiceOptions(prev => prev.map(opt => opt.id === id ? { ...opt, include_in_wr: include } : opt));
  };

  const handleRemoveServiceOption = (id: string) => {
     setCustomServiceOptions(prev => prev.filter(opt => opt.id !== id));
  };

  const handleAddManualServiceOption = () => {
     setCustomServiceOptions(prev => [
       ...prev, 
       { id: crypto.randomUUID(), name: "Nowa Usługa", price_net: 0, category: "Opcja Serwisowa", include_in_wr: false }
     ]);
  };

  const handleUpdateFactoryOptionName = (id: string, newName: string) => {
    setCustomFactoryOptions(prev => prev.map(opt => opt.id === id ? { ...opt, name: newName } : opt));
  };

  const handleUpdateFactoryOptionPrice = (id: string, newPrice: number) => {
    setCustomFactoryOptions(prev => prev.map(opt => opt.id === id ? { ...opt, price_net: newPrice } : opt));
  };

  const handleRemoveFactoryOption = (id: string) => {
     setCustomFactoryOptions(prev => prev.filter(opt => opt.id !== id));
  };

  const handleUpdateFactoryOptionNoDiscount = (id: string, noDiscount: boolean) => {
     setCustomFactoryOptions(prev => prev.map(opt => opt.id === id ? { ...opt, no_discount: noDiscount } : opt));
  };

  const handleAddManualFactoryOption = () => {
     setCustomFactoryOptions(prev => [
       ...prev, 
       { id: crypto.randomUUID(), name: "Nowa Opcja Fabryczna", price_net: 0, category: "Fabryczna", no_discount: false }
     ]);
  };

  const handleRestoreAllOptions = () => {
    if (window.confirm("Czy na pewno chcesz przywrócić oryginalne usługi serwisowe i opcje fabryczne wyekstrahowane z dokumentu bazy? Bieżące niezapisane modyfikacje zostaną utracone.")) {
      setCustomServiceOptions(initialServiceOptions);
       setCustomFactoryOptions(initialFactoryOptions);
    }
  };

  // Store full homologation response temporarily
  const [homologationResult, setHomologationResult] = useState<HomologationResponse | null>(null);

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();

    const verifyHomologation = async () => {
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const mappedData = vehicle.synthesis_data?.mapped_ai_data as any;
        // Default base payload if missing (for now using 1000kg as fallback or extracting from real schema later)
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const basePayload = (vehicle.synthesis_data as any)?.card_summary?.technical_details?.payload_capacity_kg || 1500;
        
        const payload = {
          vehicle_id: vehicle.id,
          base_samar_category: mappedData?.samar_category,
          base_vehicle_type: mappedData?.vehicle_type,
          base_payload_kg: basePayload,
          service_options: customServiceOptions.map(opt => ({
             name: opt.name,
             category: opt.category,
             price_net: opt.price_net,
             effects: opt.effects
          }))
        };

        const res = await apiClient.fetch(`/api/homologation/verify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal: controller.signal
        });

        if (!res.ok) return;
        const data = await res.json();
        if (mounted) {
          // console.log("HOMO Response raw:", Array.isArray(data) ? data[0] : data);
          setHomologationResult(Array.isArray(data) ? data[0] : data);
        }
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          // silently fail verification
        }
      }
    };

    const timeout = setTimeout(verifyHomologation, 600);
    return () => {
      mounted = false;
      clearTimeout(timeout);
      controller.abort();
    };
  }, [customServiceOptions, vehicle.id, vehicle.synthesis_data]);

  const [isSavingServices, setIsSavingServices] = useState(false);

  const handleSaveAllOptions = async () => {
    setIsSavingServices(true);
    try {
      const currentSynthesis = vehicle.synthesis_data as Record<string, unknown> || {};
      const updatedJson = JSON.parse(JSON.stringify(currentSynthesis));
      
      if (!updatedJson.card_summary) updatedJson.card_summary = {};
      
      updatedJson.card_summary.paid_options = [
        ...customFactoryOptions.map(opt => ({
           name: opt.name,
           category: opt.category,
           price: String(opt.price_net) + " PLN netto",
           price_net: opt.price_net,
           no_discount: opt.no_discount
        })),
        ...customServiceOptions.map(opt => ({
           name: opt.name,
           category: opt.category,
           price: String(opt.price_net) + " PLN netto",
           price_net: opt.price_net,
           include_in_wr: opt.include_in_wr || false
        }))
      ];

      // Temporary native API call for update instead of hook to avoid refactoring whole component scope for this simple update right now
      // This will be properly separated in a future refactor step
      const { error } = await supabase
        .from("vehicle_synthesis")
        .update({ synthesis_data: updatedJson })
        .eq("id", vehicle.id);

      if (error) throw error;
      
      // Optymalizacja UX: Po zapisaniu opcji, automatycznie wyzwalamy weryfikację cech w tle,
      // żeby sekcja "Cechy Użytkowe" nadążyła za ewentualnymi zmianami w opcjach (np. polem Hak Holowniczy)
      try {
        apiClient.fetch(`/api/features/vehicle/${vehicle.id}/enrich-background`, { method: "POST" })
          .catch(e => console.error("Silent err on bg-enrich:", e));
      } catch {
        // silently ignore error
      }

      onRefresh();
    } catch (err) {
      console.error("Error saving options", err);
      // alert("Błąd podczas zapisu opcji");
    } finally {
      setIsSavingServices(false);
    }
  };

  return {
    customServiceOptions,
    customFactoryOptions,
    isSavingServices,
    homologationResult,
    handleUpdateServiceOptionName,
    handleUpdateServiceOptionPrice,
    handleUpdateServiceOptionIncludeInWr,
    handleRemoveServiceOption,
    handleAddManualServiceOption,
    handleUpdateFactoryOptionName,
    handleUpdateFactoryOptionPrice,
    handleUpdateFactoryOptionNoDiscount,
    handleRemoveFactoryOption,
    handleAddManualFactoryOption,
    handleRestoreAllOptions,
    handleSaveAllOptions,
  };
}

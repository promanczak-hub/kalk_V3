import type { FleetVehicleView } from "../../types";

interface VehicleSummaryCardProps {
  vehicle: FleetVehicleView;
}

const EMPTY = "—";

function val(v: string | null | undefined): string {
  if (!v || v === "Brak" || v === "-") return EMPTY;
  return v;
}

interface RowProps {
  label: string;
  value: string;
}

function Row({ label, value }: RowProps) {
  return (
    <tr className="border-b border-slate-100 last:border-b-0">
      <td className="py-2 pr-6 text-xs text-slate-400 whitespace-nowrap align-top">
        {label}
      </td>
      <td className="py-2 text-sm text-slate-800 font-medium">{value}</td>
    </tr>
  );
}

export function VehicleSummaryCard({ vehicle }: VehicleSummaryCardProps) {
  const identityRows: RowProps[] = [
    { label: "Marka", value: val(vehicle.brand) },
    { label: "Model", value: val(vehicle.model) },
    { label: "Wersja", value: val(vehicle.trim_level) },
    { label: "Typ nadwozia", value: val(vehicle.body_style) },
    { label: "Kategoria", value: val(vehicle.document_category) },
  ];

  const techRows: RowProps[] = [
    { label: "Napęd", value: val(vehicle.powertrain) },
    { label: "Paliwo", value: val(vehicle.fuel) },
    { label: "Skrzynia biegów", value: val(vehicle.transmission) },
    { label: "Koła", value: vehicle.wheels && vehicle.wheels !== "Brak" ? `${vehicle.wheels}"` : EMPTY },
    { label: "Emisja WLTP", value: val(vehicle.emissions) },
    { label: "Kolor nadwozia", value: val(vehicle.exterior_color) },
  ];

  const metaRows: RowProps[] = [
    { label: "Numer oferty", value: val(vehicle.offer_number) },
    { label: "Kod konfiguracji", value: val(vehicle.configuration_code) },
  ];

  return (
    <div className="border border-slate-200 rounded bg-white">
      {/* Header */}
      <div className="px-5 py-3 border-b border-slate-200 bg-slate-50">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Karta podsumowania pojazdu
        </h4>
      </div>

      <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Identyfikacja */}
        <div>
          <h5 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">
            Identyfikacja
          </h5>
          <table className="w-full">
            <tbody>
              {identityRows.map((r) => (
                <Row key={r.label} {...r} />
              ))}
            </tbody>
          </table>
        </div>

        {/* Specyfikacja techniczna */}
        <div>
          <h5 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">
            Specyfikacja techniczna
          </h5>
          <table className="w-full">
            <tbody>
              {techRows.map((r) => (
                <Row key={r.label} {...r} />
              ))}
            </tbody>
          </table>
        </div>

        {/* Metadane */}
        <div>
          <h5 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">
            Metadane oferty
          </h5>
          <table className="w-full">
            <tbody>
              {metaRows.map((r) => (
                <Row key={r.label} {...r} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

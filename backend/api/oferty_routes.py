import uuid
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from core.offer_generator import ExcelOfferGenerator
from core.database import supabase

router = APIRouter()


class OfferItem(BaseModel):
    id: Optional[str] = None
    brand: str = ""
    model: str = ""
    powertrain: str = ""
    vin_or_config: str = ""
    term: int = 0
    mileage: int = 0
    net_installment: float = 0.0
    contribution: float = 0.0
    system_recommendation: str = ""
    calculation_data: Dict[str, Any] = {}
    standard_equipment: List[str] = []
    factory_options: List[str] = []
    dealer_options: List[str] = []
    matrix_data: Optional[List[Dict[str, Any]]] = None


class OfferGenerateRequest(BaseModel):
    client_name: str
    client_nip: str
    items: List[OfferItem]


@router.post("/generate")
def generate_offer(request: OfferGenerateRequest):
    try:
        if not request.items:
            raise HTTPException(status_code=400, detail="Koszyk ofertowy jest pusty.")

        # Zrzucamy pydantic models to dict
        items_dict = [item.model_dump() for item in request.items]

        # Data enrichment: Fetch matrix and full equipment if missing
        for item in items_dict:
            # Metadata resolution
            calc_data = item.get("calculation_data", {})
            vehicle_id = item.get("vehicle_id") or calc_data.get("vehicle_id")
            calc_id = item.get("kalkulacja_id") or calc_data.get("kalkulacja_id")

            # 1. Fetch Matrix Data if missing but we have IDs
            if not item.get("matrix_data") and (calc_id or vehicle_id):
                query = supabase.table("vehicle_matrix_cache").select("*")
                if calc_id:
                    query = query.eq("kalkulacja_id", calc_id)
                else:
                    # Fallback to last known calculation for this vehicle if specific calc_id is missing
                    query = (
                        query.eq("vehicle_id", vehicle_id)
                        .order("created_at", desc=True)
                        .limit(20)
                    )

                matrix_res = query.execute()
                if matrix_res.data:
                    item["matrix_data"] = matrix_res.data

            # 2. Fetch Full Equipment from vehicle_synthesis if missing
            if vehicle_id and (
                not item.get("standard_equipment") or not item.get("factory_options")
            ):
                synth_res = (
                    supabase.table("vehicle_synthesis")
                    .select("synthesis_data")
                    .eq("id", vehicle_id)
                    .execute()
                )
                if synth_res.data:
                    synth = synth_res.data[0].get("synthesis_data", {})
                    digital_twin = synth.get("digital_twin", [])

                    # Normalization: If digital_twin is a dict, treat values as lists
                    all_features = []
                    if isinstance(digital_twin, list):
                        all_features = digital_twin
                    elif isinstance(digital_twin, dict):
                        for k, v in digital_twin.items():
                            if isinstance(v, list):
                                all_features.extend(v)
                            else:
                                all_features.append(f"{k}: {v}")

                    # Standard Equipment
                    if not item.get("standard_equipment"):
                        item["standard_equipment"] = all_features

                    # Factory Options - extract common patterns if not explicitly provided
                    if not item.get("factory_options"):
                        opts = []
                        for f in all_features:
                            if isinstance(f, dict):
                                f_str = f.get("name", str(f))
                            else:
                                f_str = str(f)
                            if any(
                                x in f_str.lower()
                                for x in [
                                    "pakiet",
                                    "lakier",
                                    "felgi",
                                    "tapicerka",
                                    "opcja",
                                ]
                            ):
                                opts.append(f_str)
                        item["factory_options"] = (
                            opts if opts else ["Specyfikacja wg standardu producenta"]
                        )

        # Init generatora (generowanie natywne openpyxl)
        generator = ExcelOfferGenerator()

        # Generowanie pliku binarnie
        excel_bytes = generator.generate_offer(
            client_name=request.client_name,
            client_nip=request.client_nip,
            items=items_dict,
        )

        # Unikalna nazwa pliku - z timestampem i nazwa klienta
        client_clean = "".join([c if c.isalnum() else "_" for c in request.client_name])
        filename = (
            f"oferta_{int(time.time())}_{client_clean}_{str(uuid.uuid4())[:8]}.xlsx"
        )

        # Zapis fizyczny pliku w Supabase Storage bucket 'offers_excel'
        try:
            supabase.storage.from_("offers_excel").upload(
                path=filename,
                file=excel_bytes,
                file_options={
                    "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                },
            )
            # Pobranie wygenerowanego publicznego URL
            file_url = supabase.storage.from_("offers_excel").get_public_url(filename)
        except Exception as storage_err:
            print(f"Storage Error: {storage_err}")
            # If storage fails (e.g. missing bucket), we still want to save the record in DB
            # with a placeholder or handle it. For now, let's raise a specific message.
            raise HTTPException(
                status_code=500,
                detail=f"Błąd zapisu w chmurze (Bucket 'offers_excel' prawdopodobnie nie istnieje). Proszę o utworzenie bucketu w Supabase Dashboard. Błąd: {str(storage_err)}",
            )

        # Odkładamy ślad w ltr_offers - archiwizacja stawek (JSONB object)
        supabase.table("ltr_offers").insert(
            [
                {
                    "client_name": request.client_name,
                    "client_nip": request.client_nip,
                    "total_calculations": len(items_dict),
                    "offer_snapshot": items_dict,
                    "excel_file_path": file_url,
                }
            ]
        ).execute()

        return {
            "success": True,
            "url": file_url,
            "message": "Oferta została poprawnie wygenerowana i zarchiwizowana.",
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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


class OfferGenerateRequest(BaseModel):
    client_name: str
    client_nip: str
    items: List[OfferItem]


@router.post("/generate")
async def generate_offer(request: OfferGenerateRequest):
    try:
        if not request.items:
            raise HTTPException(status_code=400, detail="Koszyk ofertowy jest pusty.")

        # Zrzucamy pydantic models to dict
        items_dict = [item.model_dump() for item in request.items]

        # Init generatora (szablon w backend/templates)
        generator = ExcelOfferGenerator(template_path="templates/template_oferta.xlsx")

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
        upload_resp = supabase.storage.from_("offers_excel").upload(
            path=filename,
            file=excel_bytes,
            file_options={
                "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            },
        )

        # Pobranie wygenerowanego publicznego URL (jeszcze lepiej get_public_url)
        # Biorę URL bez względu na odpowiedź uplaodu - upload() samo rzuci StorageException jeśli blad
        file_url = supabase.storage.from_("offers_excel").get_public_url(filename)

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

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

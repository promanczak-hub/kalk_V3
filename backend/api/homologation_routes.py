from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/homologation", tags=["Homologation"])


class ModificationEffect(BaseModel):
    override_samar_class: Optional[str] = None
    override_homologation: Optional[str] = None
    adds_weight_kg: Optional[float] = None
    is_financial_only: bool = False


class ServiceOptionPayload(BaseModel):
    name: str
    category: str
    price_net: Optional[float] = None
    effects: Optional[ModificationEffect] = None


class HomologationRequest(BaseModel):
    vehicle_id: Optional[str] = None
    base_samar_category: Optional[str] = None
    base_vehicle_type: Optional[str] = None
    base_payload_kg: Optional[float] = None
    service_options: List[ServiceOptionPayload] = []


class HomologationResponse(BaseModel):
    new_samar_category: Optional[str] = None
    new_vehicle_type: Optional[str] = None
    payload_loss_kg: float = 0.0
    dynamic_payload_kg: Optional[float] = None
    homologation_alerts: List[str] = []
    samar_override_applied: bool = False


@router.post("/verify", response_model=HomologationResponse)
def verify_homologation(payload: HomologationRequest):
    new_samar = payload.base_samar_category
    new_homologation = payload.base_vehicle_type
    total_weight_loss = 0.0
    alerts = []
    overriden = False

    # Analyze each option for homologation impact
    for opt in payload.service_options:
        # If it has explicit effects defined by AI:
        if opt.effects and not opt.effects.is_financial_only:
            if opt.effects.override_samar_class:
                new_samar = opt.effects.override_samar_class
                overriden = True
                alerts.append(f"Zabudowa '{opt.name}' wymusza klasę SAMAR: {new_samar}")

            if opt.effects.override_homologation:
                new_homologation = opt.effects.override_homologation
                alerts.append(
                    f"Zabudowa '{opt.name}' zmienia kategorię homologacyjną na: {new_homologation}"
                )

            if opt.effects.adds_weight_kg:
                total_weight_loss += opt.effects.adds_weight_kg
        else:
            # Basic textual deduction if effects are missing (manual entry)
            # This can be later expanded with NLP or keyword matching.
            name_lower = opt.name.lower()
            if "izoterma" in name_lower:
                new_samar = "Izoterma"
                overriden = True
                alerts.append(f"Wykryto zabudowę izotermiczną z nazwy: '{opt.name}'")
            elif "kontener" in name_lower:
                new_samar = "Kontener"
                overriden = True
                alerts.append(f"Wykryto zabudowę kontenerową z nazwy: '{opt.name}'")
            elif "skrzynia" in name_lower or "skrzyniow" in name_lower:
                new_samar = "Skrzyniowy"
                overriden = True
                alerts.append(f"Wykryto zabudowę skrzyniową z nazwy: '{opt.name}'")
            elif "chłodnia" in name_lower or "chlodnia" in name_lower:
                new_samar = "Chłodnia"
                overriden = True
                alerts.append(f"Wykryto zabudowę chłodniczą z nazwy: '{opt.name}'")
            elif "hak" in name_lower and payload.base_vehicle_type != "Ciągnik":
                # Hak sam w sobie nie zmienia samar_class_name dostawczaków, ale dokłada wagę
                pass

    dynamic_payload = None
    if payload.base_payload_kg is not None:
        dynamic_payload = payload.base_payload_kg - total_weight_loss
        if dynamic_payload < 0:
            alerts.append(
                f"KRYTYCZNE: Ujemna ładowność! Brakuje {abs(dynamic_payload)} kg względem parametrów bazowych."
            )
        elif dynamic_payload < 300:
            alerts.append(
                f"Uwaga: Po dodaniu zabudów ładowność wyniesie tylko {dynamic_payload} kg."
            )

    return HomologationResponse(
        new_samar_category=new_samar,
        new_vehicle_type=new_homologation,
        payload_loss_kg=total_weight_loss,
        dynamic_payload_kg=dynamic_payload,
        homologation_alerts=alerts,
        samar_override_applied=overriden,
    )

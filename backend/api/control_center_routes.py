from fastapi import APIRouter, HTTPException

from core.control_center import fetch_control_center_settings
from core.models import ControlCenterSettings

router = APIRouter(tags=["Control Center"])


@router.get("/control-center")
async def get_control_center() -> ControlCenterSettings:
    try:
        return fetch_control_center_settings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

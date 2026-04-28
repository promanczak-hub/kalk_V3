from typing import Any, cast

from fastapi import APIRouter, HTTPException

from core.database import supabase
from core.models import ControlCenterSettings

router = APIRouter(tags=["Control Center"])


@router.get("/control-center")
async def get_control_center() -> ControlCenterSettings:
    try:
        response = supabase.table("control_center").select("*").eq("id", 1).execute()
        if not response.data:
            raise HTTPException(
                status_code=404, detail="Control center settings not found"
            )
        response_data = cast(Any, response.data[0])
        return ControlCenterSettings(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

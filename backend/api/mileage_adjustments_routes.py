from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.database import supabase

router = APIRouter(tags=["Mileage Adjustments"])


class MileageAdjustmentBase(BaseModel):
    max_mileage_target: int
    correction_below_threshold: float
    correction_above_threshold: float


class MileageAdjustment(MileageAdjustmentBase):
    id: str  # UUID
    samar_class_id: int
    samar_class_name: Optional[str] = None


class MileageAdjustmentUpdate(MileageAdjustmentBase):
    pass


@router.get("/mileage-adjustments", response_model=List[MileageAdjustment])
def get_mileage_adjustments():
    """
    Fetch all mileage adjustments with their corresponding SAMAR class names.
    """
    try:
        response = (
            supabase.table("samar_mileage_adjustments")
            .select("*, samar_classes(name)")
            .order("samar_class_id")
            .execute()
        )

        result = []
        for row in response.data:
            adj = MileageAdjustment(
                id=row["id"],
                samar_class_id=row["samar_class_id"],
                max_mileage_target=row["max_mileage_target"],
                correction_below_threshold=row["correction_below_threshold"],
                correction_above_threshold=row["correction_above_threshold"],
                samar_class_name=row.get("samar_classes", {}).get("name")
                if row.get("samar_classes")
                else None,
            )
            result.append(adj)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/mileage-adjustments/{adjustment_id}", response_model=MileageAdjustment)
def update_mileage_adjustment(adjustment_id: str, payload: MileageAdjustmentUpdate):
    """
    Update a specific mileage adjustment.
    """
    try:
        update_data = {
            "max_mileage_target": payload.max_mileage_target,
            "correction_below_threshold": payload.correction_below_threshold,
            "correction_above_threshold": payload.correction_above_threshold,
        }

        response = (
            supabase.table("samar_mileage_adjustments")
            .update(update_data)
            .eq("id", adjustment_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Adjustment not found")

        row = response.data[0]
        # We don't join on update response, so just return the updated base
        return MileageAdjustment(
            id=row["id"],
            samar_class_id=row["samar_class_id"],
            max_mileage_target=row["max_mileage_target"],
            correction_below_threshold=row["correction_below_threshold"],
            correction_above_threshold=row["correction_above_threshold"],
            samar_class_name=None,  # Will be missing in the immediate response, frontend shouldn't care
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

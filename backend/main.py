from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Structured logging (must be first import to configure root logger) ──
import core.logger  # noqa: F401 — side-effect: configures structlog

from api.samar_rv_routes import router as samar_rv_router
from api.parser_routes import router as parser_router
from api.kalkulacje_routes import router as kalkulacje_router
from api.calculator_excel_data_routes import router as calculator_excel_data_router
from api.extract_routes import router as extract_router
from api.homologation_routes import router as homologation_router
from api.param_preview import router as param_preview_router
from api.features_routes import router as features_router
from api.features_admin_routes import router as features_admin_router
from api.config_crud_routes import config_crud_router
from api.catalog_routes import router as catalog_router
from api.excel_draft_routes import router as excel_draft_router
from api.tab_okres_final_routes import router as tab_okres_final_router
from api.body_types_routes import router as body_types_routes_router
from api.body_type_wr_corrections_routes import (
    router as body_type_wr_corrections_router,
)

from api.admin_insurance_routes import router as admin_insurance_router
from api.mileage_adjustments_routes import router as mileage_adjustments_router

from api.control_center_admin_routes import router as control_center_admin_router
from api.calculator_core_routes import router as calculator_core_router
from api.vehicle_features_crud_routes import router as vehicle_features_crud_router
from api.pdf_parser_routes import router as pdf_parser_router
from api.scoring_search_routes import router as scoring_search_router
from api.oferty_routes import router as oferty_router
from api.brochure_routes import router as brochure_router
from api.sheets_sync_routes import router as sheets_sync_router
from core.auth_middleware import get_current_user
from core.settings import FRONTEND_ORIGINS

app = FastAPI(
    title="Kalkulator LTR V3 Engine",
    version="3.0.0",
    dependencies=[Depends(get_current_user)],
)


@app.on_event("startup")
async def _startup_redis_probe() -> None:
    """Probe Redis on startup so logs show connection status."""
    from core.redis_cache import is_redis_available

    status = "connected" if is_redis_available() else "unavailable (fallback lru_cache)"
    import logging

    logging.getLogger("main").info("Redis status on startup: %s", status)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Public health check — exempt from auth."""
    from core.redis_cache import is_redis_available

    return {
        "status": "ok",
        "version": "3.0.0",
        "redis_status": "connected" if is_redis_available() else "unavailable",
    }


app.include_router(samar_rv_router)
app.include_router(parser_router, prefix="/api")
app.include_router(extract_router, prefix="/api")
app.include_router(kalkulacje_router, prefix="/api")
app.include_router(calculator_excel_data_router, prefix="/api")
app.include_router(homologation_router, prefix="/api")
app.include_router(param_preview_router, prefix="/api")
app.include_router(features_router, prefix="/api")
app.include_router(features_admin_router, prefix="/api")
app.include_router(config_crud_router, prefix="/api")
app.include_router(catalog_router, prefix="/api")
app.include_router(excel_draft_router, prefix="/api")
app.include_router(tab_okres_final_router, prefix="/api")
app.include_router(body_types_routes_router, prefix="/api")
app.include_router(body_type_wr_corrections_router, prefix="/api")

app.include_router(admin_insurance_router, prefix="/api")
app.include_router(control_center_admin_router, prefix="/api")
app.include_router(calculator_core_router, prefix="/api")
app.include_router(vehicle_features_crud_router, prefix="/api")
app.include_router(pdf_parser_router, prefix="/api")
app.include_router(scoring_search_router, prefix="/api")
app.include_router(oferty_router, prefix="/api/offers", tags=["Oferty"])
app.include_router(brochure_router, prefix="/api")
app.include_router(mileage_adjustments_router, prefix="/api")
app.include_router(sheets_sync_router, prefix="/api")

frontend_origins_str = FRONTEND_ORIGINS
if frontend_origins_str == "*":
    allow_origins = ["*"]
else:
    allow_origins = [
        origin.strip() for origin in frontend_origins_str.split(",") if origin.strip()
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    from granian import Granian

    Granian(
        "main:app",
        address="0.0.0.0",
        port=8000,
        interface="asgi",
        reload=True,
    ).serve()

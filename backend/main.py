from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.samar_rv_routes import router as samar_rv_router
from api.parser_routes import router as parser_router
from api.kalkulacje_routes import router as kalkulacje_router
from api.budget_finder_routes import router as budget_finder_router
from api.calculator_excel_data_routes import router as calculator_excel_data_router
from api.extract_routes import router as extract_router
from api.homologation_routes import router as homologation_router
from api.param_preview import router as param_preview_router
from api.features_routes import router as features_router
from api.features_admin_routes import router as features_admin_router
from api.config_crud_routes import config_crud_router
from api.base_rv_routes import router as base_rv_router
from api.catalog_routes import router as catalog_router
from api.excel_draft_routes import router as excel_draft_router
from api.document_library_routes import router as document_library_router
from api.admin_insurance_routes import router as admin_insurance_router

from api.control_center_admin_routes import router as control_center_admin_router
from api.calculator_core_routes import router as calculator_core_router
from api.vehicle_features_crud_routes import router as vehicle_features_crud_router
from core.settings import FRONTEND_ORIGINS

app = FastAPI(title="Kalkulator LTR V2 Engine", version="1.0.0")
app.include_router(samar_rv_router)
app.include_router(parser_router, prefix="/api")
app.include_router(extract_router, prefix="/api")
app.include_router(kalkulacje_router, prefix="/api")
app.include_router(budget_finder_router, prefix="/api")  # type: ignore
app.include_router(calculator_excel_data_router, prefix="/api")
app.include_router(homologation_router, prefix="/api")
app.include_router(param_preview_router, prefix="/api")
app.include_router(features_router, prefix="/api")
app.include_router(features_admin_router, prefix="/api")
app.include_router(config_crud_router, prefix="/api")
app.include_router(base_rv_router, prefix="/api", tags=["Control Center"])
app.include_router(catalog_router, prefix="/api")
app.include_router(excel_draft_router, prefix="/api")
app.include_router(document_library_router, prefix="/api")
app.include_router(admin_insurance_router, prefix="/api")
app.include_router(control_center_admin_router, prefix="/api")
app.include_router(calculator_core_router, prefix="/api")
app.include_router(vehicle_features_crud_router, prefix="/api")

frontend_origins_str = FRONTEND_ORIGINS
if frontend_origins_str == "*":
    allow_origins = ["*"]
else:
    allow_origins = [origin.strip() for origin in frontend_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



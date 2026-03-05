from pydantic import BaseModel


class ControlCenterSettings(BaseModel):
    default_wibor: float
    default_ltr_margin: float
    default_depreciation_pct: float
    vat_rate: float
    bank_spread: float
    samar_segment_b_adjustment: int
    samar_segment_c_adjustment: int
    samar_segment_d_adjustment: int
    value_threshold_1: float
    value_threshold_2: float
    resale_time_days: int
    inventory_financing_cost: float
    samar_rv_apply_color_correction: bool
    samar_rv_apply_body_correction: bool
    samar_rv_apply_options_depreciation: bool
    samar_rv_base_mileage: int
    samar_rv_mileage_unit_km: int

    # Parametry ubezpieczeń V1 (Kradzież, Szkoda)
    ins_theft_doub_pct: float
    ins_driving_school_doub_pct: float
    ins_avg_damage_value: float
    ins_avg_damage_mileage: int
    ins_nnw_annual_rate: float
    ins_ass_annual_rate: float
    ins_green_card_annual_rate: float

    # Koszty Dodatkowe
    cost_gsm_subscription_monthly: float
    cost_gsm_device: float
    cost_gsm_installation: float
    cost_hook_installation: float
    cost_grid_dismantling: float
    cost_registration: float
    cost_sales_prep: float

    # Normatywny przebieg floty (floor dla kosztu serwisu)
    normatywny_przebieg_mc: int = 1667  # km/mc (= 20 000 km/rok)

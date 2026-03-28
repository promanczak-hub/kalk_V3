from pydantic import BaseModel


class ControlCenterSettings(BaseModel):
    default_wibor: float
    default_ltr_margin: float
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

    # Parametry ubezpieczeń V1 (Szkoda)
    ins_avg_damage_value: float
    ins_avg_damage_mileage: int
    ins_nnw_annual_rate: float
    ins_ass_annual_rate: float
    ins_green_card_annual_rate: float

    # Koszty Dodatkowe
    cost_gsm_subscription_monthly: float
    cost_gsm_device: float
    cost_gsm_installation: float
    gsm_amortization_years: float = 4.0
    cost_hook_installation: float
    cost_grid_dismantling: float
    cost_registration: float
    cost_sales_prep: float
    cost_transport: float = 0.0

    # Normatywny przebieg floty (floor dla kosztu serwisu)
    normatywny_przebieg_mc: int = 1666  # km/mc (ok. 20 000 km/rok)

    # Współczynnik WR dla ceny sprzedaży LO: WRdlaLO = WR × (1 + lo_param)
    przewidywana_cena_sprzedazy_lo: float = 0.15
    budzet_marketingowy_ltr: float = 0.0
    last_settings_update: str = ""  # ISO datetime from DB

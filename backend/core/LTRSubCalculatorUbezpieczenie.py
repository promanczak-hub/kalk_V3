from dataclasses import dataclass


@dataclass
class InsuranceInput:
    base_price: float
    months: int
    ac_rate_pct: float
    oc_rate_annual: float
    depreciation_rate_pct: float  # e.g., 0.98% drop per month -> 0.0098

    # Optional flags and their rates
    theft_doub_rate_pct: float
    add_theft_insurance: bool

    manual_correction_gross: float
    annual_damage_risk: float
    vat_rate: float

    express_pays_insurance: bool


@dataclass
class InsuranceResult:
    total_cost_net: float
    monthly_cost_net: float
    uncharged_total: float


class InsuranceCalculator:
    def __init__(self, data: InsuranceInput):
        self.data = data
        self.LICZBA_LAT = 7

    def calculate(self) -> InsuranceResult:
        total_cost_period = 0.0

        ac_rate_combined = self.data.ac_rate_pct
        if self.data.add_theft_insurance:
            ac_rate_combined += self.data.theft_doub_rate_pct

        # Loop exactly up to 7 years, but accumulate only for months of the lease
        for year in range(self.LICZBA_LAT):
            # Calculate total months strictly BEFORE this year
            liczba_miesiecy_przed_rokiem = year * 12

            # If we've already covered all required months, exit loop
            if liczba_miesiecy_przed_rokiem >= self.data.months:
                break

            # V1 logic: base drops linearly each month
            depreciation_factor = 1.0 - (
                liczba_miesiecy_przed_rokiem * self.data.depreciation_rate_pct
            )
            if depreciation_factor < 0:
                depreciation_factor = 0.0

            podstawa_naliczania = self.data.base_price * depreciation_factor

            # Yearly AC part
            yearly_ac = podstawa_naliczania * (ac_rate_combined / 100.0)

            # Yearly OC part is fixed
            yearly_oc = self.data.oc_rate_annual

            # Yearly total for this simulated year includes damage risk
            yearly_total = yearly_ac + yearly_oc + self.data.annual_damage_risk

            # Pro-rate if this is the last, partial year
            miesiecy_pozostalo = self.data.months - liczba_miesiecy_przed_rokiem
            if miesiecy_pozostalo < 12:
                # Add only the fraction of the year
                total_cost_period += yearly_total * (miesiecy_pozostalo / 12.0)
            else:
                # Add full year
                total_cost_period += yearly_total

        cost_for_contract = total_cost_period

        # Add manual correction
        manual_net = 0.0
        if self.data.vat_rate > 0:
            manual_net = self.data.manual_correction_gross / self.data.vat_rate

        total_uncharged = cost_for_contract + manual_net

        # Financial logic override based on express_pays_insurance
        effective_total = total_uncharged if self.data.express_pays_insurance else 0.0

        return InsuranceResult(
            total_cost_net=effective_total,
            monthly_cost_net=effective_total / self.data.months
            if self.data.months > 0
            else 0.0,
            uncharged_total=total_uncharged,
        )

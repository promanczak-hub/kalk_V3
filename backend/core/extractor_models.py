from enum import Enum
from typing import Annotated, List, Literal, Optional
from pydantic import BaseModel, Field, WithJsonSchema


# ─────────────────────────────────────────────────────────────────────────
# V3 EXTRACTION HELPERS — source grounding + price reconciliation
# ─────────────────────────────────────────────────────────────────────────


class OffsetSpan(BaseModel):
    """Page+bbox grounding for a value extracted from a PDF.

    Used by V3 extraction pipeline (langextract or fallback) to record WHERE in
    the source PDF a value came from. Powers HITL highlight in the frontend
    PDF viewer.
    """

    page: int = Field(description="1-indexed PDF page number where the value appears")
    bbox: Optional[List[float]] = Field(
        default=None,
        description=(
            "[x1, y1, x2, y2] bounding box on the page (PDF coordinates). "
            "None when only page-level grounding is available (fallback path)."
        ),
    )
    quoted_text: Optional[str] = Field(
        default=None,
        description="Literal text excerpt from the PDF that justifies the value.",
    )
    from_visual: bool = Field(
        default=False,
        description=(
            "True if the value came from a diagram/drawing (not a text layer). "
            "UI highlights the whole page in this case."
        ),
    )


class FieldOffset(BaseModel):
    """Mapping of a top-level CardSummary field name → its source offsets."""

    field_path: str = Field(
        description="Dot-path to the field (e.g. 'base_price', 'dimensions.length_mm')"
    )
    spans: List[OffsetSpan] = Field(default_factory=list)


# Conversion provenance for net/gross/vat reconciliation. Mirrors
# `core.price_inference.ConversionSource` Literal type.
ConversionSourceLiteral = Literal[
    "explicit_both",
    "computed_from_net",
    "computed_from_gross",
    "unknown",
]


class PackageItem(BaseModel):
    package_name: Optional[str] = Field(None, description="The name of the package")
    price: Optional[float] = Field(None, description="Price of the package")
    contents: List[str] = Field(
        default_factory=list, description="Features or items included in this package"
    )


class EquipmentItem(BaseModel):
    name: str = Field(..., description="Name of the equipment option")
    price: float = Field(
        ..., description="Price of the option, exactly 0.0 if standard or free"
    )
    code: Optional[str] = Field(
        None, description="PR Code or manufacturer code if available"
    )


class StandardEquipmentCategory(BaseModel):
    category: str = Field(..., description="Categorized area (e.g. Wnętrze, Nadwozie)")
    items: List[EquipmentItem] = Field(
        default_factory=list,
        description="List of standard equipment items with 0.0 prices",
    )


class TireInfo(BaseModel):
    brand: Optional[str] = Field(None, description="Brand of the tire")
    model: Optional[str] = Field(None, description="Tire model")
    size: Optional[str] = Field(None, description="Tire size")
    decibels: Optional[str] = Field(None, description="Noise level in dB")


class FinancialData(BaseModel):
    base_price_gross: float = Field(
        ..., description="Base vehicle price (Gross/Brutto)"
    )
    options_price_gross: Optional[float] = Field(
        None, description="Optional equipment sum (Gross/Brutto)"
    )
    total_discount_gross: Optional[float] = Field(
        None, description="Total discount applied (Gross/Brutto)"
    )
    final_price_gross: float = Field(
        ..., description="Final vehicle price (Gross/Brutto)"
    )
    currency: str = Field("PLN", description="Currency code")


class TechnicalData(BaseModel):
    engine_type: Optional[str] = Field(None, description="Engine description")
    power_hp: Optional[int] = Field(None, description="Power in Horsepower (KM)")
    power_kw: Optional[int] = Field(None, description="Power in Kilowatts (kW)")
    transmission: Optional[str] = Field(None, description="Gearbox type")
    dimensions_length_mm: Optional[int] = Field(None, description="Length in mm")
    dimensions_width_mm: Optional[int] = Field(None, description="Width in mm")
    dimensions_wheelbase_mm: Optional[int] = Field(None, description="Wheelbase in mm")
    weight_curb_kg: Optional[int] = Field(None, description="Curb weight in kg")
    weight_gross_kg: Optional[int] = Field(
        None, description="Gross vehicle weight in kg"
    )
    ev_battery_capacity_kwh: Optional[float] = Field(
        None, description="Battery capacity in kWh"
    )
    ev_range_wltp_km: Optional[int] = Field(
        None, description="Electric range WLTP in km"
    )
    ev_charging_time: Optional[str] = Field(None, description="Charging time AC/DC")


class VisualIdentity(BaseModel):
    exterior_paint_name: str = Field(
        ..., description="Name of the exterior paint (e.g. Szary Daytona)"
    )
    exterior_paint_code: Optional[str] = Field(
        None, description="Code of the exterior paint"
    )
    interior_upholstery_material: Optional[str] = Field(
        None, description="Material of the upholstery"
    )
    interior_upholstery_color: Optional[str] = Field(
        None, description="Color of the seats/upholstery"
    )
    interior_dashboard_color: Optional[str] = Field(
        None, description="Color of the dashboard"
    )


class Metadata(BaseModel):
    offer_number: Optional[str] = Field(None, description="Offer or quote number")
    configuration_code: Optional[str] = Field(
        None, description="Configuration code (e.g., Kod Audi, BMW Code)"
    )
    configuration_id: Optional[str] = Field(None, description="Configuration ID")
    creation_date: Optional[str] = Field(None, description="Document creation date")
    valid_until: Optional[str] = Field(None, description="Offer valid until")


class FinancingOptions(BaseModel):
    financing_type: Optional[str] = Field(
        None, description="Type of financing (e.g. Perfect Lease)"
    )
    duration_months: Optional[int] = Field(None, description="Duration in months")
    down_payment_gross: Optional[float] = Field(
        None, description="Down payment (Gross/Brutto)"
    )
    monthly_installment_gross: Optional[float] = Field(
        None, description="Monthly installment (Gross/Brutto)"
    )
    yearly_mileage_limit_km: Optional[int] = Field(
        None, description="Yearly mileage limit"
    )


class WarrantyService(BaseModel):
    extended_warranty_years: Optional[int] = Field(
        None, description="Years of extended warranty"
    )
    extended_warranty_mileage_km: Optional[int] = Field(
        None, description="Max mileage of extended warranty"
    )
    service_package: Optional[str] = Field(
        None, description="Included service package details"
    )


class VehicleAISynthesis(BaseModel):
    brand: Optional[str] = Field(
        None, description="Brand of the vehicle (e.g. Audi, VW)"
    )
    model: Optional[str] = Field(
        None, description="Model of the vehicle (e.g. A5 Sportback, Golf)"
    )
    trim_level: Optional[str] = Field(
        None,
        description="Trim level or equipment version (e.g., S line, AMG Line, R-Line)",
    )
    dealer_info: Optional[str] = Field(
        None, description="Full extracted dealer and client info (PII)"
    )
    metadata: Optional[Metadata] = Field(
        None, description="Document and offer lifecycle metadata"
    )
    visual_identity: Optional[VisualIdentity] = Field(
        None, description="Exterior paint and interior styling"
    )
    technical_data: Optional[TechnicalData] = None
    tires_info: List[TireInfo] = Field(default_factory=list)
    standard_equipment: List[StandardEquipmentCategory] = Field(default_factory=list)
    optional_equipment: List[EquipmentItem] = Field(default_factory=list)
    packages: List[PackageItem] = Field(default_factory=list)
    financing: Optional[FinancingOptions] = Field(
        None, description="Leasing / loan simulations"
    )
    warranty_service: Optional[WarrantyService] = Field(
        None, description="Warranty and service packages"
    )
    financials: FinancialData


class NapedTyp(str, Enum):
    BENZYNA_ICE = "Benzyna (PB)"
    DIESEL_ICE = "Diesel (ON)"
    BENZYNA_MHEV = "Benzyna mHEV (PB-mHEV)"
    DIESEL_MHEV = "Diesel mHEV (ON-mHEV)"
    HEV = "Hybryda (HEV)"
    PHEV = "Hybryda Plug-in (PHEV)"
    BEV = "Elektryczny (BEV)"
    FCEV = "Wodór (FCEV)"
    LPG = "Autogaz (LPG)"


class NapedRodzaj(str, Enum):
    FWD = "FWD"
    RWD = "RWD"
    AWD = "AWD"


class TransmissionTyp(str, Enum):
    """Znormalizowany rodzaj skrzyni biegów. SOT: tabela `public.transmission_types`
    (synced z Google Sheet 'transmission_dict')."""

    MANUALNA = "Manualna"
    AUTOMATYCZNA = "Automatyczna"


class PrzedzialMocy(str, Enum):
    LOW = "LOW (do 130 KM)"
    MID = "MID (131 - 200 KM)"
    HIGH = "HIGH (201 KM i więcej)"


# --- V2 CARD SUMMARY (Flash LLM Output) ---


class DiscountExtractionMethod(str, Enum):
    """Sposób w jaki rabat został zidentyfikowany w dokumencie."""

    EXPLICIT_AMOUNT = "explicit_amount"
    EXPLICIT_PERCENTAGE = "explicit_percentage"
    COMPUTED_FROM_TOTAL = "computed_from_total"
    NONE = "none"


class DiscountBreakdown(BaseModel):
    """Strukturalny opis rabatu udzielonego w ofercie dealera.

    Rozdziela 'co widzę literalnie' od 'co wyliczyłem' i jawnie modeluje
    kwoty NIE objęte rabatem (zabudowy dealera, akcesoria pozafabryczne).
    """

    explicit_rabat_pln: Optional[float] = Field(
        None,
        description=(
            "Kwota rabatu DOKŁADNIE odczytana z dokumentu (np. linia 'RABAT 42 317,-'). "
            "Wpisuj TYLKO jeśli widnieje literalnie w dokumencie. "
            "NIE wyliczaj. NIE zgaduj. → null jeśli brak."
        ),
    )
    explicit_rabat_pct: Optional[float] = Field(
        None,
        description=(
            "Procent rabatu LITERALNIE odczytany (np. 'Rabat 24%' / '-12%'). "
            "Wpisuj TYLKO jeśli widnieje literalnie. → null jeśli brak."
        ),
    )
    discountable_base_net: Optional[float] = Field(
        None,
        description=(
            "Kwota netto, do której rabat się odnosi (= base_price + factory_options). "
            "WAŻNE: NIE wliczaj tu zabudowy/wyposażenia dealera/modyfikacji karoserii. "
            "Te pozycje zwykle NIE podlegają rabatowi producenta."
        ),
    )
    non_discountable_total_net: Optional[float] = Field(
        None,
        description=(
            "Suma pozycji NIE objętych rabatem (zabudowa wywrotka/kontener/izoterma, "
            "akcesoria dealera, modyfikacje karoserii, GPS, hak dealerski). "
            "Wlicza się do total_price, ale NIE do podstawy rabatu."
        ),
    )
    computed_pct: Optional[float] = Field(
        None,
        description=(
            "Wyliczone matematycznie jako (explicit_rabat_pln / discountable_base_net) × 100. "
            "Zaokrąglij do 2 miejsc po przecinku. Wyliczaj zawsze gdy masz oba inputy."
        ),
    )
    extraction_method: DiscountExtractionMethod = Field(
        DiscountExtractionMethod.NONE,
        description=(
            "Skąd pochodzi rabat: 'explicit_amount' (kwota PLN przepisana), "
            "'explicit_percentage' (procent przepisany), 'computed_from_total' "
            "(wyliczony pośrednio z różnicy cen — najmniej pewne), 'none' (brak rabatu)."
        ),
    )
    confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description=(
            "Pewność ekstrakcji rabatu (0.0-1.0). 1.0 = explicit + triangulacja zgadza się. "
            "0.5 = wyliczony pośrednio. 0.6 = explicit ale arytmetyka się nie zgadza."
        ),
    )
    audit_notes: list[str] = Field(
        default_factory=list,
        description=(
            "Notatki audytowe — np. 'Triangulacja: 145485 + 31732 - 42317 = 134900 ✓', "
            "'Zabudowa wywrotka 31732 zł oznaczona jako non-discountable'."
        ),
    )
    rabat_type: Optional[Literal["kwotowo", "procentowo"]] = Field(
        default=None,
        description=(
            "Typ rabatu wybrany przez użytkownika w HITL: 'kwotowo' (rabat to "
            "stała kwota PLN) lub 'procentowo' (rabat to % od bazy). "
            "Wypełniane przez wizard HITL, LLM zostawia null."
        ),
    )
    rabat_basis: Optional[Literal["netto", "brutto"]] = Field(
        default=None,
        description=(
            "Baza rabatu wybrana przez użytkownika w HITL: czy rabat liczony "
            "od netto czy brutto. Wypełniane przez wizard HITL."
        ),
    )
    discount_scope: list[Literal["base", "factory_options", "zabudowa", "agregat"]] = Field(
        default_factory=list,
        description=(
            "Bucket-y do których stosuje się rabat (HITL): "
            "['base', 'factory_options'] = klasyczny scope rabatu producenta; "
            "lista pusta = ekstrakcja jeszcze nie potwierdzona przez user'a."
        ),
    )


class PaidOption(BaseModel):
    name: str = Field(description="Nazwa płatnej opcji")
    price: str = Field(
        description="Cena płatnej opcji z walutą i typem netto/brutto "
        "(np. '2750 PLN netto' lub '5476 PLN brutto')"
    )
    price_type: str = Field(
        default="unknown",
        description="Typ ceny: 'netto', 'brutto' lub 'unknown'. "
        "Wywniosuj z etykiet w dokumencie lub odziedzicz z price_domain.",
    )
    category: str = Field(
        description="Kategoria opcji (np. 'Fabryczna' lub 'Serwisowa/Akcesoria')"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Pewność (0.0-1.0): 1.0=z PDF, 0.8=jednoznaczna pochodna, 0.5=niejednoznaczna, 0.0=halucynacja.",
    )
    field_id: str = Field(
        default="",
        description=(
            "Stabilny identyfikator pozycji dla HITL diff (uuid4). "
            "Generowany backend-side po ekstrakcji — LLM zostawia puste."
        ),
    )
    # ── V3 fields (price_inference + dedup; backend-filled or LLM-provided) ──
    net_amount: Optional[float] = Field(
        default=None,
        description=(
            "Cena netto jako liczba (PLN). LLM zwraca jeśli widzi wprost w PDF; "
            "w przeciwnym razie backend wylicza z `price` + `price_type` przez "
            "`price_inference.infer_price_pair`. NIGDY nie zakładaj VAT=23% — "
            "polegaj na `vat_rate`."
        ),
    )
    gross_amount: Optional[float] = Field(
        default=None,
        description=(
            "Cena brutto jako liczba (PLN). Analogicznie do net_amount — "
            "albo z PDF (explicit), albo wyliczona z `net_amount * (1+vat_rate)`."
        ),
    )
    vat_rate: Optional[float] = Field(
        default=None,
        description=(
            "Stawka VAT jako ułamek dziesiętny (0.23 = 23%, 0.08 = 8%, 0.0 = export). "
            "LLM wyciąga DOKŁADNIE z dokumentu — nie zakłada 23% domyślnie. "
            "null = nieznana, backend wyciąga z relacji net↔gross jeśli oba znane."
        ),
    )
    conversion_source: Optional[ConversionSourceLiteral] = Field(
        default=None,
        description=(
            "Skąd wzięły się net_amount/gross_amount: 'explicit_both' (oba w PDF), "
            "'computed_from_net' (gross policzony), 'computed_from_gross' (net policzony), "
            "'unknown' (jedna wartość bez VAT). Wypełnia backend (price_inference)."
        ),
    )
    canonical_id: str = Field(
        default="",
        description=(
            "Hash znormalizowanej nazwy + ceny — sygnał dla HITL że dwa kafelki "
            "wyglądają jak duplikat. Wypełnia backend (dedup.compute_canonical_id), "
            "LLM zostawia puste."
        ),
    )
    duplicate_of: Optional[str] = Field(
        default=None,
        description=(
            "Inny field_id wykryty jako prawdopodobny duplikat. NIE oznacza auto-drop — "
            "tylko sygnał dla HITL (różowe obramowanie + opcja merge w UI)."
        ),
    )
    source_offsets: Optional[List[OffsetSpan]] = Field(
        default=None,
        description=(
            "Lista offsetów w PDF (page+bbox+quoted_text) uzasadniających tę pozycję. "
            "Frontend HITL używa do highlightowania w PDF viewerze. "
            "None jeśli ekstrakcja nie produkowała offsetów."
        ),
    )


class ServiceComponentItem(BaseModel):
    name: str = Field(
        description="Nazwa elementu składowego (np. element zabudowy lub pod-pakiet)"
    )
    price_net: str = Field(description="Cena netto elementu (z walutą)")
    price_gross: str = Field(description="Cena brutto elementu (z walutą)")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "Pewność ekstrakcji tego komponentu (0.0-1.0). Skala identyczna jak "
            "PaidOption.confidence: 1.0/0.8/0.5/0.0. 0.0 = halucynacja, brak źródła."
        ),
    )
    field_id: str = Field(
        default="",
        description="Stabilny identyfikator komponentu dla HITL diff (uuid4).",
    )
    # ── V3 fields ──
    net_amount: Optional[float] = Field(default=None, description="Cena netto (PLN, liczba)")
    gross_amount: Optional[float] = Field(default=None, description="Cena brutto (PLN, liczba)")
    vat_rate: Optional[float] = Field(default=None, description="Stawka VAT (ułamek; 0.23, 0.08, …)")
    conversion_source: Optional[ConversionSourceLiteral] = Field(default=None)
    canonical_id: str = Field(default="")
    duplicate_of: Optional[str] = Field(default=None)
    source_offsets: Optional[List[OffsetSpan]] = Field(default=None)


class ServiceEquipment(BaseModel):
    name: str = Field(
        description="Główna nazwa komponentu serwisowego / zabudowy (np. 'Pakiet Przeglądów (PRO+FLASH)', 'Zabudowa izotermiczna'). Nazwij ten komponent sensownie na podstawie kontekstu."
    )
    total_price_net: str = Field(description="Kwota netto całości (wraz z walutą)")
    total_price_gross: str = Field(description="Kwota brutto całości (wraz z walutą)")
    components: list[ServiceComponentItem] = Field(
        default_factory=list,
        description="Składowe komponentu (jeśli suma składa się z elementów lub relacja kwot na to wskazuje). Gemini powinien zwrócić każdą opcję osobno z netto/brutto.",
    )
    # ── V3 fields ──
    field_id: str = Field(
        default="",
        description="Stabilny identyfikator dla HITL (backend-filled jeśli LLM zostawi puste).",
    )
    net_amount: Optional[float] = Field(default=None, description="Cena netto całości (PLN, liczba)")
    gross_amount: Optional[float] = Field(default=None, description="Cena brutto całości (PLN, liczba)")
    vat_rate: Optional[float] = Field(default=None, description="Stawka VAT (ułamek)")
    conversion_source: Optional[ConversionSourceLiteral] = Field(default=None)
    canonical_id: str = Field(default="")
    duplicate_of: Optional[str] = Field(default=None)
    source_offsets: Optional[List[OffsetSpan]] = Field(default=None)


class UtilityFeatureItem(BaseModel):
    name: str = Field(
        description="Nazwa parametry liczbowego (np. Wymiary przedziału ładunkowego (dł.), Pojemność przestrzeni ładunkowej, Objętość, Długość pojazdu)"
    )
    value: str = Field(
        description="Wartość z jednostką (np. 3450 mm, 14.4 m3, 1140 kg). Przekaż absolutnie bez zmian z pliku."
    )


class CargoAndDimensions(BaseModel):
    length_mm: Optional[int] = Field(None, description="Długość całkowita (w mm)")
    width_mm: Optional[int] = Field(None, description="Szerokość (w mm, bez lusterek)")
    height_mm: Optional[int] = Field(None, description="Wysokość całkowita (w mm)")
    wheelbase_mm: Optional[int] = Field(None, description="Rozstaw osi (w mm)")

    cargo_length_mm: Optional[int] = Field(
        None, description="Długość przedziału ładunkowego / paki (w mm)"
    )
    cargo_width_mm: Optional[int] = Field(
        None, description="Szerokość przedziału ładunkowego (w mm)"
    )
    cargo_height_mm: Optional[int] = Field(
        None, description="Wysokość przedziału ładunkowego (w mm)"
    )
    cargo_volume_m3: Optional[float] = Field(
        None, description="Objętość / kubatura przestrzeni ładunkowej (w m3)"
    )

    curb_weight_kg: Optional[int] = Field(
        None, description="Masa własna pojazdu (w kg)"
    )
    payload_kg: Optional[int] = Field(
        None, description="Ładowność (w kg) - szczególnie ważne dla dostawczych"
    )
    gross_vehicle_weight_kg: Optional[int] = Field(
        None, description="DMC (dopuszczalna masa całkowita, np. 3500 kg)"
    )

    fuel_tank_capacity_l: Optional[int] = Field(
        None, description="Pojemność zbiornika paliwa (w litrach)"
    )


class CardSummary(BaseModel):
    financial_reasoning: str = Field(
        description="Krótka analiza cen z dokumentu — relacje między base, options, total (szczegółowe zasady w system prompt).",
    )
    price_domain: str = Field(
        default="unknown",
        description="Domena cenowa dokumentu: 'netto', 'brutto' lub 'unknown' (szczegółowe reguły w system prompt).",
    )
    base_price: str = Field(
        description="Cena katalogowa bazowa (bez rabatów i opustów) wraz z walutą i przyrostkiem 'netto' lub 'brutto' wywnioskowanym z relacji kwot lub wprost z dokumentu (np. '100 000 PLN netto'). Zwróć 'Brak' jeśli nie znaleziono."
    )
    options_price: str = Field(
        description="Łączna cena opcji dodatkowo płatnych z walutą i przyrostkiem 'netto' lub 'brutto'. Zwróć 'Brak' jeśli nie znaleziono."
    )
    total_price: str = Field(
        description="Podsumowanie łączna cena (końcowa / po upuście / oferta dealera) z walutą i przyrostkiem 'netto' lub 'brutto' wywnioskowanym z relacji kwot lub wprost z dokumentu (np. '120 000 PLN netto'). Zwróć 'Brak' jeśli nie znaleziono."
    )
    offer_discount_pct: Optional[str] = Field(
        default=None,
        description=(
            "[LEGACY — preferuj `discount.computed_pct`] Rabat w procentach jako string. "
            "Wypełniaj dla wstecznej kompatybilności wartością z `discount.computed_pct`."
        ),
    )
    offer_discount_pln: Optional[str] = Field(
        default=None,
        description=(
            "[LEGACY — preferuj `discount.explicit_rabat_pln`] Rabat kwotowy jako string. "
            "Wypełniaj dla wstecznej kompatybilności wartością z `discount.explicit_rabat_pln`."
        ),
    )
    discount: Optional[DiscountBreakdown] = Field(
        default=None,
        description=(
            "Strukturalny breakdown rabatu z oferty dealera. "
            "Rozdziela kwoty objęte rabatem (base + opcje fabryczne) od pozycji "
            "niepodlegających rabatowi (zabudowa dealera, akcesoria, modyfikacje karoserii). "
            "Wykonaj DRZEWKO DECYZYJNE z sekcji 'EKSTRAKCJA RABATU' w prompcie."
        ),
    )
    powertrain: str = Field(
        description="Silnik + moc (KM/HP). Buduj z pojemności + technologii (TDI/TSI/e-Tech) + mocy, jeśli brak w tabelach."
    )
    vehicle_class: str = Field(
        description="Klasa pojazdu na podstawie oceny całego dokumentu. Musi być to ściśle jedna z dwóch wartości: 'Osobowy' lub 'Dostawczy'."
    )
    engine_capacity: Optional[str] = Field(
        None,
        description="Pojemność silnika, np. '1.5', '2.0'. Zwróć 'Brak' lub null, jeśli nie dotyczy lub brakuje informacji.",
    )
    engine_designation: Optional[str] = Field(
        None,
        description=(
            "Oznaczenie handlowe silnika, np. 'TSI', 'TDI', 'dCi', 'EcoBoost'. "
            "Dla m-HEV/mHEV — dołącz do oznaczenia (np. 'TSI m-HEV', 'TDI mHEV')."
        ),
    )
    engine_marketing_name: Optional[str] = Field(
        None,
        description=(
            "Marketingowa nazwa silnika/technologii (np. 'ECO-G', 'BlueHDi', 'e-Tech', 'Hybrid 136'). "
            "Dla m-HEV/mHEV — wpisz dokładnie 'm-HEV' (lub 'mHEV') nawet jeśli już w engine_designation."
        ),
    )
    engine_category: Optional[str] = Field(
        None,
        description=(
            "Kategoria napędu: jedna z wartości NapedTyp (np. 'Benzyna (PB)', "
            "'Diesel (ON)', 'Benzyna mHEV (PB-mHEV)', 'Diesel mHEV (ON-mHEV)'). "
            "Dla m-HEV/mHEV wybierz wariant mHEV nawet jeśli silnik to TSI/TDI."
        ),
    )
    power_hp: Optional[int] = Field(
        None,
        description=(
            "Wyciągnięta moc pojazdu in koniach mechanicznych (KM) jako liczba całkowita "
            "(int). Szukaj 'KM', 'HP', 'PS'. Jeśli widzisz tylko 'kW', pomnóż przez 1.36 "
            "i zwróć jako int. Jeśli moc ukryta jest w nazwie wersji (np. 'Crafter Kombi "
            "103 kW'), wyciągnij i przelicz."
        ),
    )
    power_range: Optional[str] = Field(
        None,
        description="Przedział mocy w KM: 'LOW (do 130 KM)', 'MID (131 - 200 KM)' lub 'HIGH (201 KM i więcej)'.",
    )
    fuel: str = Field(
        description=(
            "Rodzaj paliwa, np. 'Diesel', 'Benzyna', 'Benzyna mHEV', 'Diesel mHEV', "
            "'Hybryda PHEV', 'Elektryczny'. Dla mHEV/MHEV — użyj wariantu mHEV "
            "(nie upraszczaj do 'Benzyna'). 'Brak' jeśli nie znaleziono."
        )
    )
    power_kw: Optional[int] = Field(
        None,
        description="Wyciągnięta moc pojazdu w kilowatach (kW) jako liczba całkowita (int).",
    )
    dimensions: Optional[CargoAndDimensions] = Field(
        None,
        description="Wyciągnięte wymiary, masy i ładowność bezpośrednio z PDF.",
    )
    drive_type: Optional[str] = Field(
        None,
        description=(
            "Rodzaj napędu: 'FWD', 'RWD' lub 'AWD'. "
            "'4x4' i 'ALL' → 'AWD'. '4x2' i '2x4' → 'FWD' (2x4 = dwa koła napędzane z czterech)."
        ),
    )
    transmission: str = Field(
        description="Rodzaj skrzyni biegów, np. 'Automatyczna', 'Manualna', 'DSG'. Zwróć 'Brak' jeśli nie przypisano."
    )
    number_of_seats: Optional[int] = Field(
        None, description="Liczba miejsc siedzących (np. 2, 5, 7, 9)."
    )
    has_automatic_ac: Optional[bool] = Field(
        None, description="Czy pojazd posiada klimatyzację automatyczną?"
    )
    body_style: str = Field(
        description=(
            "Typ nadwozia (Furgon, Kombi, SUV, Hatchback, Pickup, Liftback itd.). "
            "Dedukuj z nazwy modelu jeśli brak wprost (Octavia Combi → Kombi)."
        )
    )
    trim_level: str = Field(
        description=(
            "Wersja wyposażenia lub wariant nadwozia (np. 'S line', 'Furgon z wysokim "
            "dachem'). Szukaj oznaczenia obok modelu bazowego. Zwróć 'Brak' "
            "jeśli nie przypisano."
        )
    )
    wheels: str = Field(
        description="Tylko i wyłącznie średnica felgi (kół) wyrażona jako liczba (np. '17', '18'). Zwracaj uwagę na słowa takie jak: 'Obręcze', 'Felgi', 'Kute' w dokumencie, następnie wyciągnij samą średnicę nominalną. Zwróć 'Brak' jeśli nie znaleziono."
    )
    emissions: str = Field(
        description="Emisja spalin (np. '123 g/km') i opcjonalnie zużycie paliwa (np. '6.5 l/100km'). Szukaj słów: 'WLTP', 'Zużycie', 'Spalanie', 'Emisja CO2'. Zwróć 'Brak' jeśli nie znaleziono."
    )
    exterior_color: str = Field(
        description="Kolor lakieru nadwozia (wraz z dopłatą na rzecz lakieru, np. 'lakier metallic 3500 zł brutto' lub 'netto'). Zwróć 'Brak' jeśli nie znaleziono."
    )
    standard_equipment: list[str] = Field(
        description="Lista wyposażenia standardowego — wszystkie pozycje z wszystkich sekcji, oryginalne nazwy, bez filtrowania trywialnych (ABS/ESP/ISOFIX itd.). Tylko dokładne duplikaty pomiń.",
    )
    paid_options: list[PaidOption] = Field(
        description="Lista osobnych, płatnych opcji dodatkowych uwzględnionych w konfiguracji podanych w postaci listy z nazwą ew. kodem opcji i ceną dopłaty (wraz z 'netto' lub 'brutto')."
    )
    service_equipment: Optional[ServiceEquipment] = Field(
        None,
        description="Szczegóły dotyczące opcji serwisowej, pakietów przeglądów lub zabudowy (jeśli występuje na dokumencie). Zawiera kwoty netto/brutto całości oraz podzespołów.",
    )
    has_tow_hook: Optional[bool] = Field(
        None,
        description="Czy pojazd ma zamontowany hak holowniczy (lub przygotowanie pod hak). Zwróć True jeśli znaleziono, False jeśli wprost nie ma, null jeśli brak informacji.",
    )
    is_metalic_paint: Optional[bool] = Field(
        None,
        description=(
            "Czy lakier nadwozia jest z kategorii premium (metalik, perłowy, xirallic, "
            "mica, special efekt, dwuwarstwowy) — zwróć True. Lakier bazowy, akrylowy, "
            "jednowarstwowy, solido — zwróć False. Chodzi o kategorię lakieru, NIE o cenę "
            "(nawet darmowy lakier metalik = True). Null jeśli brak informacji."
        ),
    )
    is_current_year_vehicle: Optional[bool] = Field(
        None,
        description=(
            "True jeśli pojazd z bieżącego/przyszłego rocznika, False jeśli poprzedni, null jeśli brak danych. "
            "Bazuj na dacie oferty / roku modelowym / dacie produkcji."
        ),
    )
    vin: Optional[str] = Field(
        None,
        description=(
            "Numer VIN pojazdu (Vehicle Identification Number) — 17-znakowy ciąg alfanumeryczny. "
            "Szukaj etykiet: 'VIN', 'Nr VIN', 'Numer VIN', 'Numer nadwozia', 'Nr nadwozia', "
            "'Identyfikator pojazdu', 'Chassis No', 'Fahrgestellnummer'. "
            "Przepisuj DOKŁADNIE bez spacji i myślników. Zwróć null jeśli nie znaleziono."
        ),
    )
    suggested_discount_pct: Optional[float] = Field(
        None,
        description="Wyliczony przez AI sugerowany procent rabatu na podstawie dopasowania auta do oficjalnej macierzy rabatowej (np. 12.5). Zostaw puste, jeśli nie dopasowano.",
    )
    available_powertrains: list[str] = Field(
        description="Zestawienie dostępnych wariantów napędowych, np. ['50 (125 kW)', '60 (150 kW)', '85 (210 kW)']"
    )
    available_trims: list[str] = Field(
        description="Lista głównych wersji wyposażeniowych występujących w dokumencie, np. ['Essence', 'Selection', 'Sportline']"
    )
    starting_price: str = Field(
        description="Cena bazowa, od której startuje najtańszy wariant modelu, z walutą i np. netto/brutto, jeśli występuje."
    )
    key_technologies: list[str] = Field(
        description="Kluczowe nowinki technologiczne uwypuklone w broszurze, np. ['Reflektory Matrix LED', 'System AI MIB4']"
    )
    confidence_score: float = Field(
        default=1.0,
        description="Ocena pewności AI (0.00-1.00) względem poprawności wyodrębnionych danych, zwłaszcza cen i specyfikacji technicznej. Bądź krytyczny!",
    )
    ai_warnings: list[str] = Field(
        default_factory=list,
        description="Lista potencjalnych nieścisłości zauważonych przez AI (np. 'Niepewność co do przynależności opcji do pakietu', 'Dwie różne ceny w tekście').",
    )
    confidence_breakdown: Annotated[
        dict[str, float],
        WithJsonSchema(
            {
                "type": "object",
                "properties": {
                    "base_price": {"type": "number"},
                    "options_price": {"type": "number"},
                    "total_price": {"type": "number"},
                    "body_style": {"type": "number"},
                    "discount.rabat_pct": {"type": "number"},
                    "engine_class": {"type": "number"},
                    "samar_category": {"type": "number"},
                    "trim_level": {"type": "number"},
                },
            }
        ),
    ] = Field(
        default_factory=dict,
        description=(
            "Confidence per najważniejsze pole top-level (0.0-1.0). Klucze: "
            "'base_price', 'options_price', 'total_price', 'body_style', "
            "'discount.rabat_pct', 'engine_class', 'samar_category', 'trim_level'. "
            "Skala: 1.0/0.8/0.5/0.0 (patrz PaidOption.confidence). "
            "Pole z confidence 0.0 = halucynacja, ma trafić do _hallucinated_fields."
        ),
    )
    hallucinated_fields: list[str] = Field(
        default_factory=list,
        description=(
            "Lista field_path-ów które LLM oznaczył confidence=0.0 (halucynacje). "
            "Wypełniane backend-side post-process — LLM zostawia puste. "
            "Wymusza verification_status='needs_review' niezależnie od innych pól."
        ),
    )
    # ────────────────────────────────────────────────────────────────────
    # V3 NUMERIC PRICE FIELDS (deterministic VAT triangulation)
    # ────────────────────────────────────────────────────────────────────
    # Old `base_price: str` ("100 000 PLN netto") stays for backward compat.
    # New numeric fields are populated by pipeline_normalization via
    # price_inference.infer_price_pair. Allow None when LLM/PDF don't supply.
    base_price_net: Optional[float] = Field(
        default=None,
        description="Cena katalogowa bazowa netto (liczba PLN). Wypełnia backend z `base_price` przez price_inference.",
    )
    base_price_gross: Optional[float] = Field(
        default=None,
        description="Cena katalogowa bazowa brutto (liczba PLN).",
    )
    base_price_vat: Optional[float] = Field(
        default=None,
        description="Stawka VAT zastosowana dla base_price (ułamek; 0.23/0.08/0.0). null=nieznana.",
    )
    options_price_net: Optional[float] = Field(default=None)
    options_price_gross: Optional[float] = Field(default=None)
    options_price_vat: Optional[float] = Field(default=None)
    total_price_net: Optional[float] = Field(default=None)
    total_price_gross: Optional[float] = Field(default=None)
    total_price_vat: Optional[float] = Field(default=None)

    # ── V3 source grounding (powers HITL highlight) ──
    source_offsets_by_field: Optional[List[FieldOffset]] = Field(
        default=None,
        description=(
            "Mapowanie pole→offset(y) dla top-level fields. Powers PDF viewer "
            "highlight w HITL. None gdy ekstrakcja v2/legacy (bez offsetów)."
        ),
    )


# ─────────────────────────────────────────────────────────────────────────
# V3 RAW EXTRACTION (PASS A) — literal quotes from PDF, pre-normalization
# ─────────────────────────────────────────────────────────────────────────


class RawPriceLine(BaseModel):
    """One literal price/value line as quoted from the PDF.

    Pass A output — Gemini Pro extracts these verbatim with grounding offsets,
    Pass B (pipeline_normalization) then VAT-triangulates, categorizes,
    dedup-flags and maps them onto CardSummary fields.
    """

    quoted_text: str = Field(description="Literalny fragment tekstu z PDF")
    role: str = Field(
        description=(
            "Rola tej kwoty: 'base_price', 'options_total', 'total_price', "
            "'discount', 'paid_option', 'service_total', 'service_component', "
            "'other'."
        )
    )
    net_amount: Optional[float] = Field(default=None)
    gross_amount: Optional[float] = Field(default=None)
    vat_rate: Optional[float] = Field(default=None)
    label: Optional[str] = Field(
        default=None,
        description="Etykieta przy kwocie z PDF (np. 'netto', 'brutto', 'po rabacie')",
    )
    offsets: List[OffsetSpan] = Field(default_factory=list)


class RawOptionLine(BaseModel):
    """One literal option/equipment line from the PDF (paid option, component)."""

    name: str
    quoted_text: Optional[str] = Field(default=None)
    net_amount: Optional[float] = Field(default=None)
    gross_amount: Optional[float] = Field(default=None)
    vat_rate: Optional[float] = Field(default=None)
    category_hint: Optional[str] = Field(
        default=None,
        description="Heurystyczna kategoria z PDF: 'fabryczna' | 'serwisowa' | 'zabudowa' | None",
    )
    offsets: List[OffsetSpan] = Field(default_factory=list)


class RawExtractionResult(BaseModel):
    """Pass A output — RAW literal quotes from a PDF, pre-normalization."""

    document_language: Optional[str] = Field(
        default=None,
        description="Wykryty język oferty (ISO 639-1 lub None gdy niepewne).",
    )
    document_currency: Optional[str] = Field(
        default=None, description="Waluta dominująca w PDF (PLN/EUR/USD/…). None gdy niepewne."
    )
    raw_prices: List[RawPriceLine] = Field(default_factory=list)
    raw_options: List[RawOptionLine] = Field(default_factory=list)
    raw_dimension_lines: List[RawPriceLine] = Field(
        default_factory=list,
        description=(
            "Wartości techniczne/fizyczne wyciągnięte z rysunków (długość, szerokość, "
            "wysokość, masa). role='dimension', offsets z `from_visual=true` gdy z rysunku."
        ),
    )
    multi_vehicle_evidence: Optional[str] = Field(
        default=None,
        description=(
            "Cytat z PDF wskazujący na obecność wielu RÓŻNYCH pojazdów "
            "(np. 'oferta na 3 modele: Caddy 1.5, Caddy 2.0, Transporter')."
        ),
    )


class OtherDocumentSummary(BaseModel):
    summary: str = Field(description="Ogólne podsumowanie zawartego dokumentu.")
    key_points: list[str] = Field(
        description="Najważniejsze punkty lub regulacje wylistowane z dokumentu."
    )


# --- V3 SERVICE OPTIONS DIGITAL TWIN ---


class VehicleModificationEffects(BaseModel):
    override_samar_class: Optional[str] = Field(
        None,
        description="Ewentualna nowa klasa SAMAR jeśli modyfikacja zmienia charakter pojazdu (np. Autobus, Izoterma, Kontener, Skrzyniowy, Dostawczy)",
    )
    override_homologation: Optional[str] = Field(
        None, description="Opcjonalna kategoria homologacyjna (np. N1, N2, M1)"
    )
    adds_weight_kg: Optional[float] = Field(
        None, description="Dodatkowa masa własna w kg wynikająca z modyfikacji"
    )
    is_financial_only: bool = Field(
        False,
        description="Zaznacz true jeśli to tylko koszt (np. dywaniki, opony, hak) w przeciwieństwie do zabudowy",
    )


class ServiceOptionDigitalTwin(BaseModel):
    name: str = Field(
        description="Zwięzła nazwa usługi / zabudowy / przedmiotu wywnioskowana z dokumentu"
    )
    net_price: float = Field(description="Wyciągnięta całkowita kwota netto w PLN")
    description_or_components: list[str] = Field(
        default_factory=list,
        description="Lista kluczowych komponentów lub parametrów opisujących tę usługę",
    )
    effects: Optional[VehicleModificationEffects] = Field(
        default=None,
        description="Szczegółowa kategoryzacja wpływu tej opcji na parametry fizyczne i klasy pojazdu",
    )


class ServiceOptionExtractionResult(BaseModel):
    service_options: list[ServiceOptionDigitalTwin] = Field(
        default_factory=list,
        description="Lista wszystkich opcji serwisowych i zabudów wykrytych w dokumencie.",
    )


# --- V3 BROCHURE EXTRACTOR SCHEMA ---


class BrochureEquipmentCategory(BaseModel):
    category_name: str = Field(
        description="Dynamiczna nazwa kategorii, w jakiej występuje to wyposażenie, np. 'Bezpieczeństwo', 'Wnętrze', 'Pakiety, 'Media i Nawigacja'. Niech model sam ułoży logiczne grupy."
    )
    items: list[str] = Field(
        description="Lista szczegółowych elementów w tej kategorii, z pominięciem jakichkolwiek cen.",
        default_factory=list,
    )


class VehicleBrochureSchema(BaseModel):
    brand: Optional[str] = Field(None, description="Marka pojazdu")
    model: Optional[str] = Field(None, description="Model pojazdu")
    trim_level: Optional[str] = Field(
        None, description="Wersja wyposażenia pojazdu, np. 'S line', 'AMG'"
    )
    vehicle_class: str = Field(
        description="Typ pojazdu wywnioskowany z konfiguracji: 'Osobowy' lub 'Dostawczy'"
    )

    # Technical Specs
    engine_description: Optional[str] = Field(
        None, description="Oznaczenie pojemności silnika i technologii np. '2.0 TDI'"
    )
    power_hp: Optional[int] = Field(
        None, description="Moc w Koniach Mechanicznych (KM)"
    )
    transmission: Optional[str] = Field(
        None, description="Rodzaj skrzyni biegów np. 'Automatyczna'"
    )
    drive_type: Optional[str] = Field(
        None, description="Typ napędu, np. 'Na przednią oś', 'AWD', 'quattro'"
    )

    # Dimensions & Weights
    length_mm: Optional[int] = Field(None, description="Długość pojazdu w mm")
    width_mm: Optional[int] = Field(
        None, description="Szerokość pojazdu w mm (z lusterkami lub bez)"
    )
    height_mm: Optional[int] = Field(None, description="Wysokość pojazdu w mm")
    wheelbase_mm: Optional[int] = Field(None, description="Rozstaw osi w mm")
    cargo_capacity_l: Optional[int] = Field(
        None, description="Pojemność przestrzeni bagażowej w litrach"
    )
    payload_kg: Optional[int] = Field(
        None, description="Ładowność pojazdu w kg (bardzo ważne dla aut dostawczych)"
    )

    # Performance
    acceleration_0_100: Optional[float] = Field(
        None, description="Przyspieszenie od 0 do 100 km/h w sekundach"
    )
    fuel_consumption_wltp: Optional[float] = Field(
        None, description="Zużycie paliwa / energii w trybie WLTP. (Zapisz cyfrę)"
    )
    emissions_wltp: Optional[int] = Field(
        None, description="Emisja CO2 w trybie WLTP g/km"
    )

    # Dynamic Equipment
    equipment_categories: list[BrochureEquipmentCategory] = Field(
        default_factory=list,
        description="Pełna specyfikacja wyposażeniowa samochodu zgrupowana w logiczne kategorie (m.in Wnętrze, Nadwozie, Opcje, Bezpieczeństwo). Brak jakichkolwiek cen w tej strukturze.",
    )

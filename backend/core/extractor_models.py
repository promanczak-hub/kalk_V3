from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


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
    FWD = "Napęd FWD"
    RWD = "Napęd RWD"
    AWD = "Napęd AWD"


class PrzedzialMocy(str, Enum):
    LOW = "LOW (do 130 KM)"
    MID = "MID (131 - 200 KM)"
    HIGH = "HIGH (201 KM i więcej)"


# --- V2 CARD SUMMARY (Flash LLM Output) ---


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


class ServiceComponentItem(BaseModel):
    name: str = Field(
        description="Nazwa elementu składowego (np. element zabudowy lub pod-pakiet)"
    )
    price_net: str = Field(description="Cena netto elementu (z walutą)")
    price_gross: str = Field(description="Cena brutto elementu (z walutą)")


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


class CardSummary(BaseModel):
    price_domain: str = Field(
        default="unknown",
        description="Globalna domena cenowa całego dokumentu: 'netto' lub 'brutto'. "
        "Ustal na podstawie etykiet przy cenach głównych, relacji VAT (×1.23) "
        "między kwotami, lub kontekstu dokumentu (konfigurator B2B → netto). "
        "Jeśli nie da się ustalić → 'unknown'.",
    )
    base_price: str = Field(
        description="Cena katalogowa bazowa (bez rabatów i opustów) wraz z walutą i przyrostkiem 'netto' lub 'brutto' wywnioskowanym z relacji kwot lub wprost z dokumentu (np. '100 000 PLN netto'). Zwróć 'Brak' jeśli nie znaleziono."
    )
    options_price: str = Field(
        description="Łączna cena opcji dodatkowo płatnych z walutą i przyrostkiem 'netto' lub 'brutto'. Zwróć 'Brak' jeśli nie znaleziono."
    )
    total_price: str = Field(
        description="Podsumowanie łączna cena (końcowa / po upuście / oferta dealera) z walutą i przyrostkiem 'netto' lub 'brutto'. Zwróć 'Brak' jeśli nie znaleziono."
    )
    powertrain: str = Field(
        description="Oznaczenie samego silnika i mocy, bez nazwy marki i modelu. Np. '2.0 TDI 177 KM', '1.5 TSI 150 KM', 'E-Tech EV60'. Zwróć 'Brak' jeśli nie przypisano."
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
        description="Oznaczenie handlowe silnika / technologii, np. 'TSI', 'TDI', 'dCi', 'EcoBoost'. Zwróć 'Brak' lub null, jeśli brakuje.",
    )
    engine_category: Optional[NapedTyp] = Field(
        None,
        description="Przyporządkuj rodzaj i zasilanie napędu pojazdu z dokumentu ściśle do jednej z kategorii w Enum `NapedTyp`.",
    )
    power_hp: Optional[int] = Field(
        None,
        description="Wyciągnięta moc pojazdu w koniach mechanicznych (KM) jako liczba całkowita (int).",
    )
    power_range: Optional[PrzedzialMocy] = Field(
        None,
        description="Na podstawie odczytanej mocy w KM `power_hp`, przyporządkuj pojazd do odpowiedniego przedziału opisanego w Enum `PrzedzialMocy`.",
    )
    fuel: str = Field(
        description="Rodzaj paliwa / zasilania, np. 'Diesel', 'Benzyna', 'Elektryczny', 'Hybryda PHEV', 'MHEV'. Zwróć 'Brak' jeśli nie znaleziono."
    )
    drive_type: Optional[NapedRodzaj] = Field(
        None,
        description="Rodzaj napędu (FWD, RWD, AWD). Musi być przyporządkowane do jednej z opcji Enum `NapedRodzaj` lub pozostać puste, jeśli brak jednoznacznej informacji.",
    )
    transmission: str = Field(
        description="Rodzaj skrzyni biegów, np. 'Automatyczna', 'Manualna', 'DSG'. Zwróć 'Brak' jeśli nie przypisano."
    )
    body_style: str = Field(
        description="Typ nadwozia pojazdu wywnioskowany z nazwy lub specyfikacji. Jeśli osobowy, zwróć ściśle m.in: Hatchback, Kombi, SUV, Liftback, Sedan, Coupe, Cabrio, Minivan. Jeśli dostawczy, zwróć ściśle m.in: Furgon, Pickup, Wieloosobowy, Podwozie, Van, Dwuosobowy, 5 drzwiowy VAN. Jeśli brak pewności, wybierz najbardziej prawdopodobną lub 'Brak'."
    )
    trim_level: str = Field(
        description="Wersja wyposażenia pojazdu, np. 'S line', 'AMG Line', 'R-Line', 'L&K', 'Centre-line'. Szukaj precyzyjnego oznaczenia wersji obok modelu bazowego. Zwróć 'Brak' jeśli nie przypisano."
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
        description="Lista głównych elementów wyposażenia standardowego (wypisz poszczególne nazwy/elementy, pomiń te trywialne)."
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
            "Czy pojazd jest z bieżącego rocznika produkcji (True) czy ubiegłego (False). "
            "Oceń na podstawie: daty ważności oferty, roku modelowego, daty produkcji, "
            "roku rejestracji lub innych wskazówek w dokumencie. Jeśli oferta jest "
            "wystawiona na pojazd z roku bieżącego lub przyszłego — True. Jeśli pojazd "
            "został wyprodukowany w roku poprzednim — False. Null jeśli brak danych."
        ),
    )
    suggested_discount_pct: Optional[float] = Field(
        None,
        description="Wyliczony przez AI sugerowany procent rabatu na podstawie dopasowania auta do oficjalnej macierzy rabatowej (np. 12.5). Zostaw puste, jeśli nie dopasowano.",
    )
    suggested_discount_source: Optional[str] = Field(
        None,
        description="Krótkie uzasadnienie z jakiego wiersza i na jakiej podstawie przyznano dany sugerowany rabat.",
    )


class BrochureSummary(BaseModel):
    model_description: str = Field(
        description="Krótki opis modelu generowany na podstawie broszury, np. 'Elektryczny, kompaktowy SUV wyznaczający nowy język projektowy marki.'"
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

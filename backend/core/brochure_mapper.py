from typing import Any, Dict

from core.extractor_models import (
    BrochureEquipmentCategory,
    VehicleBrochureSchema,
)


def build_brochure_from_synthesis(data: Dict[str, Any]) -> VehicleBrochureSchema:
    """
    Buduje czystą broszurę z istniejących danych (synthesis_data),
    omijając generowanie LLM jeśli dane są poprawnej struktury.
    Odróżnia formę V1 (VehicleAISynthesis) od formy V2 (CardSummary).
    """
    brand = data.get("brand")
    model = data.get("model")
    trim_level = data.get("trim_level")

    # Sprawdzamy czy to V1 czy V2
    if "financials" in data and "technical_data" in data:
        # Prawdopodobnie V1 (VehicleAISynthesis)
        return _build_from_v1(data, brand, model, trim_level)
    else:
        # Prawdopodobnie V2 (CardSummary)
        return _build_from_v2(data, brand, model, trim_level)


def _build_from_v1(
    data: Dict[str, Any], brand: str | None, model: str | None, trim_level: str | None
) -> VehicleBrochureSchema:
    tech = data.get("technical_data") or {}

    equipment_categories = []

    # Kategoria: Wyposażenie standardowe
    std_eq = data.get("standard_equipment") or []
    for cat in std_eq:
        cat_name = cat.get("category", "Wyposażenie standardowe")
        items = [item.get("name") for item in cat.get("items", []) if item.get("name")]
        if items:
            equipment_categories.append(
                BrochureEquipmentCategory(category_name=cat_name, items=items)
            )

    # Kategoria: Wyposażenie opcjonalne
    opt_eq = data.get("optional_equipment") or []
    opt_items = []
    for item in opt_eq:
        name = item.get("name")
        price = item.get("price")
        if name:
            if price and float(price) > 0:
                opt_items.append(f"{name} ({price} PLN)")
            else:
                opt_items.append(name)
    if opt_items:
        equipment_categories.append(
            BrochureEquipmentCategory(category_name="Opcje dodatkowe", items=opt_items)
        )

    # Kategoria: Pakiety
    packages = data.get("packages") or []
    for pkg in packages:
        pkg_name = pkg.get("package_name") or "Pakiet"
        pkg_price = pkg.get("price")

        cat_title = f"Pakiet: {pkg_name}"
        if pkg_price and float(pkg_price) > 0:
            cat_title += f" ({pkg_price} PLN)"

        pkg_items = pkg.get("contents") or []
        if pkg_items:
            equipment_categories.append(
                BrochureEquipmentCategory(category_name=cat_title, items=pkg_items)
            )

    return VehicleBrochureSchema(
        brand=brand,
        model=model,
        trim_level=trim_level,
        vehicle_class="Osobowy",  # domyślnie v1 częściej były osobowe, brak jawnego pola w formacie
        engine_description=tech.get("engine_type"),
        power_hp=tech.get("power_hp"),
        transmission=tech.get("transmission"),
        drive_type=None,
        length_mm=tech.get("dimensions_length_mm"),
        width_mm=tech.get("dimensions_width_mm"),
        height_mm=None,
        wheelbase_mm=tech.get("dimensions_wheelbase_mm"),
        cargo_capacity_l=None,
        payload_kg=None,
        acceleration_0_100=None,
        fuel_consumption_wltp=None,
        emissions_wltp=None,
        equipment_categories=equipment_categories,
    )


def _build_from_v2(
    data: Dict[str, Any], brand: str | None, model: str | None, trim_level: str | None
) -> VehicleBrochureSchema:
    equipment_categories = []

    # Wyposażenie standardowe
    std_items = data.get("standard_equipment") or []
    if std_items:
        equipment_categories.append(
            BrochureEquipmentCategory(
                category_name="Wyposażenie standardowe", items=std_items
            )
        )

    # Opcje dodatkowe
    paid_opts = data.get("paid_options") or []
    # Grupujemy opcje płatne po ich `category` (często 'Fabryczna', 'Serwisowa')
    opt_dict: Dict[str, list[str]] = {}
    for opt in paid_opts:
        cat_name = opt.get("category", "Opcje dodatkowe")
        name = opt.get("name")
        price = opt.get("price")

        if name:
            item_str = name
            # price is usually a string like '1500 PLN netto'
            if price and price.lower() != "brak":
                # Check if it has an actual number to avoid "0 PLN"
                try:
                    import re

                    nums = re.findall(r"\d+", price)
                    if nums and int(nums[0]) > 0:
                        item_str = f"{name} ({price})"
                except Exception:
                    item_str = f"{name} ({price})"
            opt_dict.setdefault(cat_name, []).append(item_str)

    for cat_name, items in opt_dict.items():
        if items:
            equipment_categories.append(
                BrochureEquipmentCategory(category_name=cat_name, items=items)
            )

    # Wymiary użytkowe
    utility = data.get("utility_features") or []
    utility_items = [
        f"{u.get('name')}: {u.get('value')}"
        for u in utility
        if u.get("name") and u.get("value")
    ]
    if utility_items:
        equipment_categories.append(
            BrochureEquipmentCategory(
                category_name="Cechy użytkowe (Wymiary i Masy)", items=utility_items
            )
        )

    # Wymiary z utilities
    length_mm = None
    width_mm = None
    height_mm = None
    wheelbase_mm = None
    payload_kg = None

    # Proste (naiwne) szukanie mas w utility features
    for u in utility:
        name = (u.get("name") or "").lower()
        val_str = (u.get("value") or "").lower()

        # Ekstrakcja tylko cyfr dla typowych wymiarów
        try:
            import re

            nums = re.findall(r"\d+", val_str)
            if nums:
                val_int = int(nums[0])
                if "długość" in name and "mm" in val_str:
                    length_mm = val_int
                elif "szerokość" in name and "mm" in val_str:
                    width_mm = val_int
                elif "wysokość" in name and "mm" in val_str:
                    height_mm = val_int
                elif "rozstaw osi" in name and "mm" in val_str:
                    wheelbase_mm = val_int
                elif "ładowność" in name and "kg" in val_str:
                    payload_kg = val_int
        except Exception:
            pass

    return VehicleBrochureSchema(
        brand=brand,
        model=model,
        trim_level=trim_level,
        vehicle_class=data.get("vehicle_class", "Osobowy"),
        engine_description=data.get("powertrain"),
        power_hp=data.get("power_hp"),
        transmission=data.get("transmission"),
        drive_type=data.get("drive_type"),
        length_mm=length_mm,
        width_mm=width_mm,
        height_mm=height_mm,
        wheelbase_mm=wheelbase_mm,
        cargo_capacity_l=None,
        payload_kg=payload_kg,
        acceleration_0_100=None,
        fuel_consumption_wltp=None,
        emissions_wltp=None,
        equipment_categories=equipment_categories,
    )

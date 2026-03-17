from core.brochure_mapper import build_brochure_from_synthesis

def test_build_brochure_from_v1():
    data = {
        "brand": "Audi",
        "model": "A5 Sportback",
        "trim_level": "S line",
        "technical_data": {
            "engine_type": "2.0 TFSI",
            "power_hp": 204,
            "transmission": "Automatyczna",
            "dimensions_length_mm": 4733,
            "dimensions_width_mm": 1843,
            "dimensions_wheelbase_mm": 2824
        },
        "financials": {
             "base_price_gross": 200000,
             "final_price_gross": 190000,
             "currency": "PLN"
        },
        "standard_equipment": [
            {
                "category": "Wnętrze",
                "items": [
                    {"name": "Klimatyzacja", "price": 0.0},
                    {"name": "Radio", "price": 0.0}
                ]
            }
        ],
        "optional_equipment": [
            {"name": "Lakier metalik", "price": 4000.0}
        ],
        "packages": [
            {
                "package_name": "Pakiet Comfort",
                "price": 5000.0,
                "contents": ["Podgrzewane fotele", "Kamera cofania"]
            }
        ]
    }
    
    brochure = build_brochure_from_synthesis(data)
    assert brochure.brand == "Audi"
    assert brochure.model == "A5 Sportback"
    assert brochure.trim_level == "S line"
    assert brochure.vehicle_class == "Osobowy"
    assert brochure.engine_description == "2.0 TFSI"
    assert brochure.power_hp == 204
    assert brochure.length_mm == 4733
    
    # Kategoria Wnętrze (standard)
    std_cat = next(cat for cat in brochure.equipment_categories if cat.category_name == "Wnętrze")
    assert "Klimatyzacja" in std_cat.items
    
    # Opcje
    opt_cat = next(cat for cat in brochure.equipment_categories if cat.category_name == "Opcje dodatkowe")
    assert "Lakier metalik (4000.0 PLN)" in opt_cat.items
    
    # Pakiety
    pkg_cat = next(cat for cat in brochure.equipment_categories if cat.category_name.startswith("Pakiet: Pakiet Comfort"))
    assert "Pakiet: Pakiet Comfort (5000.0 PLN)" == pkg_cat.category_name
    assert "Podgrzewane fotele" in pkg_cat.items

def test_build_brochure_from_v2():
    data = {
        "brand": "Volkswagen",
        "model": "Crafter",
        "trim_level": "Furgon",
        "vehicle_class": "Dostawczy",
        "powertrain": "2.0 TDI",
        "power_hp": 140,
        "transmission": "Manualna",
        "drive_type": "Napęd FWD",
        "standard_equipment": ["Klimatyzacja Climatic", "Radio Composition"],
        "paid_options": [
            {"name": "Kamera cofania", "price": "1000 PLN", "price_type": "netto", "category": "Opcjonalne V2"},
            {"name": "Podłoga ze sklejki", "price": "1500 PLN", "price_type": "netto", "category": "Zabudowa"}
        ],
        "utility_features": [
            {"name": "Długość", "value": "5986 mm"},
            {"name": "Szerokość", "value": "2040 mm"},
            {"name": "Wysokość przestrzeni ładunkowej", "value": "1940 mm"},
            {"name": "Ładowność", "value": "1350 kg"},
            {"name": "Rozstaw osi", "value": "3640 mm"}
        ]
    }
    
    brochure = build_brochure_from_synthesis(data)
    
    assert brochure.brand == "Volkswagen"
    assert brochure.model == "Crafter"
    assert brochure.trim_level == "Furgon"
    assert brochure.vehicle_class == "Dostawczy"
    assert brochure.engine_description == "2.0 TDI"
    assert brochure.power_hp == 140
    
    assert brochure.length_mm == 5986
    assert brochure.width_mm == 2040
    assert brochure.height_mm == 1940
    assert brochure.payload_kg == 1350
    assert brochure.wheelbase_mm == 3640
    
    std_cat = next(cat for cat in brochure.equipment_categories if cat.category_name == "Wyposażenie standardowe")
    assert "Klimatyzacja Climatic" in std_cat.items
    
    opt_cat = next(cat for cat in brochure.equipment_categories if cat.category_name == "Opcjonalne V2")
    assert "Kamera cofania (1000 PLN)" in opt_cat.items
    
    zab_cat = next(cat for cat in brochure.equipment_categories if cat.category_name == "Zabudowa")
    assert "Podłoga ze sklejki (1500 PLN)" in zab_cat.items
    
    util_cat = next(cat for cat in brochure.equipment_categories if cat.category_name == "Cechy użytkowe (Wymiary i Masy)")
    assert "Ładowność: 1350 kg" in util_cat.items

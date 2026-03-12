from core.pdf_pipeline.schemas import (
    ParsedPriceList,
    EngineVariant,
    TrimPricing,
    FeatureOption,
)
from core.pdf_pipeline.normalizer import StrictNormalizer


def test_strict_normalizer():
    # Setup data with missing prices and dirty strings
    data = ParsedPriceList(
        brand="  Volkswagen  ",
        model="Passat\n\nB8",
        engines=[
            EngineVariant(
                engine_name="   2.0 TDI   ",
                transmission="DSG",
                fuel_type="Diesel",
                prices_by_trim=[
                    TrimPricing(
                        trim_name="Elegance", price_netto=None, price_brutto=None
                    )
                ],
            )
        ],
        features=[
            FeatureOption(
                name=" Panoramic\tRoof ",
                code="  PR123  ",
                price_netto=None,
                price_brutto=None,
                applicable_trims=["  Elegance  ", "R-Line\t"],
            )
        ],
    )

    normalizer = StrictNormalizer()
    normalized = normalizer.normalize(data)

    # Check strings
    assert normalized.brand == "Volkswagen"
    assert normalized.model == "Passat B8"
    assert normalized.engines[0].engine_name == "2.0 TDI"
    assert normalized.features[0].name == "Panoramic Roof"
    assert normalized.features[0].code == "PR123"
    assert normalized.features[0].applicable_trims == ["Elegance", "R-Line"]

    # Check 0.0 enforcements
    assert normalized.engines[0].prices_by_trim[0].price_netto == 0.0
    assert normalized.engines[0].prices_by_trim[0].price_brutto == 0.0
    assert normalized.features[0].price_netto == 0.0
    assert normalized.features[0].price_brutto == 0.0

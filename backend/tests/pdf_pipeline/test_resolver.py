from core.pdf_pipeline.schemas import (
    ParsedPriceList,
    EngineVariant,
    TrimPricing,
    Footnote,
    FeatureOption,
)
from core.pdf_pipeline.resolver import FootnoteResolver


def test_resolver_no_footnotes():
    data = ParsedPriceList(
        brand="Test",
        model="Test",
        engines=[
            EngineVariant(
                engine_name="Test Engine *1",
                transmission="Manual",
                fuel_type="Gas",
                prices_by_trim=[],
            )
        ],
        footnotes=[],
    )

    resolver = FootnoteResolver()
    resolved = resolver.resolve(data)

    assert resolved.engines[0].engine_name == "Test Engine *1"


def test_resolver_with_footnotes():
    data = ParsedPriceList(
        brand="Test",
        model="Test",
        engines=[
            EngineVariant(
                engine_name="2.0 TDI *1",
                transmission="DSG *2",  # Field not mapped to be resolved intentionally for scope testing in schema
                fuel_type="Diesel",
                prices_by_trim=[TrimPricing(trim_name="Style *1", price_netto=100.0)],
            )
        ],
        features=[FeatureOption(name="Sunroof (1)", availability_rules="Requires *2")],
        footnotes=[
            Footnote(reference="*1", text="Niedostępne dla rocznika 2023"),
            Footnote(reference="*2", text="Tylko w pakiecie zimowym"),
            Footnote(reference="(1)", text="Dach panoramiczny"),
        ],
    )

    resolver = FootnoteResolver()
    resolved = resolver.resolve(data)

    # Check engine_name resolved
    assert "[*1: Niedostępne dla rocznika 2023]" in resolved.engines[0].engine_name
    assert resolved.engines[0].engine_name.startswith("2.0 TDI *1")

    # Check trim_name resolved
    assert (
        "[*1: Niedostępne dla rocznika 2023]"
        in resolved.engines[0].prices_by_trim[0].trim_name
    )

    # Check feature name resolved
    assert "[(1): Dach panoramiczny]" in resolved.features[0].name

    # Check feature availability rules resolved
    assert "[*2: Tylko w pakiecie zimowym]" in resolved.features[0].availability_rules

    # Check that original object wasn't mutated
    assert data.engines[0].engine_name == "2.0 TDI *1"


def test_resolver_multiple_footnotes_on_one_field():
    data = ParsedPriceList(
        brand="Test",
        model="Test",
        engines=[
            EngineVariant(
                engine_name="2.0 TDI *1 *2",
                transmission="DSG",
                fuel_type="Diesel",
                prices_by_trim=[],
            )
        ],
        footnotes=[
            Footnote(reference="*1", text="Niedozwolone 2024"),
            Footnote(reference="*2", text="Brak gwarancji"),
        ],
    )
    resolver = FootnoteResolver()
    resolved = resolver.resolve(data)

    assert "[*1: Niedozwolone 2024]" in resolved.engines[0].engine_name
    assert "[*2: Brak gwarancji]" in resolved.engines[0].engine_name

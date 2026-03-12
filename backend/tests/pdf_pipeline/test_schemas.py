import pytest
from pydantic import ValidationError

from core.pdf_pipeline.schemas import (
    Footnote,
    TrimPricing,
    EngineVariant,
    ParsedPriceList,
    ExtractorPipelineResult,
)


def test_footnote_validation():
    # Valid footnote
    fn = Footnote(reference="*1", text="Tylko dla wersji Style")
    assert fn.reference == "*1"
    assert fn.text == "Tylko dla wersji Style"

    # Missing required field
    with pytest.raises(ValidationError):
        Footnote(reference="*1")


def test_trim_pricing_validation():
    # Only brutto
    tp = TrimPricing(trim_name="Elegance", price_brutto=150000.0)
    assert tp.trim_name == "Elegance"
    assert tp.price_netto is None
    assert tp.price_brutto == 150000.0


def test_engine_variant_validation():
    ev = EngineVariant(
        engine_name="2.0 TDI",
        transmission="DSG",
        fuel_type="Diesel",
        power_hp=150,
        prices_by_trim=[TrimPricing(trim_name="Base", price_netto=100000.0)],
    )
    assert ev.power_hp == 150
    assert len(ev.prices_by_trim) == 1


def test_parsed_price_list_validation():
    # Test valid creation with minimal data
    pl = ParsedPriceList(brand="Skoda", model="Superb", engines=[])
    assert pl.brand == "Skoda"
    assert pl.model == "Superb"
    assert pl.features == []
    assert pl.footnotes == []

    # Missing required 'brand' and 'model'
    with pytest.raises(ValidationError):
        ParsedPriceList(brand="Skoda", engines=[])


def test_pipeline_result():
    res = ExtractorPipelineResult(is_successful=False, error_message="Zły format pliku")
    assert res.is_successful is False
    assert res.error_message == "Zły format pliku"
    assert res.parsed_data is None

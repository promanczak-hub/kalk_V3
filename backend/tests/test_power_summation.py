from core.pipeline_card_summary import _backfill_from_digital_twin


def test_power_summation_hp():
    # Setup digital twin with hybrid power format in max_power
    digital_twin = {
        "technical_data": {"engine_performance": {"max_power": "163 + 14KM"}}
    }
    card_summary = {}
    result = _backfill_from_digital_twin(card_summary, digital_twin)

    # Validation
    assert result["power_hp"] == 177
    assert result["power_range"] == "MID (131 - 200 KM)"


def test_power_summation_hp_spaces():
    digital_twin = {
        "technical_data": {"engine_performance": {"max_power": "163 KM + 14 KM"}}
    }
    card_summary = {}
    result = _backfill_from_digital_twin(card_summary, digital_twin)
    assert result["power_hp"] == 177


def test_power_summation_kw():
    digital_twin = {
        "technical_data": {"engine_performance": {"max_power": "110 + 10kW"}}
    }
    card_summary = {}
    result = _backfill_from_digital_twin(card_summary, digital_twin)

    # 120 kW * 1.36 = 163.2 -> 163 HP
    assert result["power_hp"] == 163
    assert result["power_kw"] == 120


def test_power_summation_kw_spaces():
    digital_twin = {
        "technical_data": {"engine_performance": {"max_power": "120 kW + 20 kW"}}
    }
    card_summary = {}
    result = _backfill_from_digital_twin(card_summary, digital_twin)

    # 140 kW * 1.36 = 190 HP
    assert result["power_hp"] == 190
    assert result["power_kw"] == 140


def test_power_summation_single_hp():
    digital_twin = {"technical_data": {"engine_performance": {"max_power": "204 KM"}}}
    card_summary = {}
    result = _backfill_from_digital_twin(card_summary, digital_twin)
    assert result["power_hp"] == 204


def test_power_summation_model_name_fallback():
    digital_twin = {
        "vehicle_summary": {"model_name": "Volvo XC60 B3 Mild-Hybrid 163 + 14KM"}
    }
    card_summary = {}
    result = _backfill_from_digital_twin(card_summary, digital_twin)
    assert result["power_hp"] == 177

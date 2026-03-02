import os
import sys

# Dodajemy PYTHONPATH aby pytest widzial 'core':
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock
from core.LTRSubCalculatorKosztyDodatkowe import LTRSubCalculatorKosztyDodatkowe


@pytest.fixture
def mock_supabase_responses(mocker):
    """Mocks Supabase responses to ensure isolation."""
    mock_supabase = mocker.patch("core.LTRSubCalculatorKosztyDodatkowe.supabase")

    def mock_table_select(table_name):
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_lte = MagicMock()
        mock_order = MagicMock()
        mock_limit = MagicMock()
        mock_execute = MagicMock()

        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_select.lte.return_value = mock_lte
        mock_select.order.return_value = mock_order

        # eq builder chain
        mock_eq.eq.return_value = mock_eq
        mock_eq.limit.return_value = mock_limit

        # lte builder chain
        mock_lte.order.return_value = mock_order
        mock_order.limit.return_value = mock_limit

        mock_limit.execute.return_value = mock_execute

        if "LTRAdminParametry_czak" in table_name:
            mock_execute.data = [{"col_2": "120.0"}]
        elif "KosztZabudowy" in table_name:
            mock_execute.data = [{"KosztyDodatkoweNettoRok": "1000.0"}]
        elif "KategoriaKorekta" in table_name:
            mock_execute.data = [{"WspolczynnikKorektyProcent": "1.2"}]
        elif "PrzebiegKorekta" in table_name:
            mock_execute.data = [{"WspolczynnikKorektyProcent": "0.8"}]
        else:
            mock_execute.data = []

        return mock_table

    mock_supabase.table.side_effect = mock_table_select
    return mock_supabase


def test_calculator_initialization_defaults(mock_supabase_responses):
    calc = LTRSubCalculatorKosztyDodatkowe(
        okres_uzytkowania=36,
        przebieg=60000,
        czy_gps=False,
        is_demontaz=False,
        hak=False,
        klasa_pojazdu="C",
        klasa_id=1,
        typ_zabudowy=None,
    )
    # The mocks will return 120.0 for parameters
    assert calc.vat_rate == 120.0
    assert calc.zarejestrowanie_karta_pojazdu == 120.0


def test_abonament_gsm_cost(mock_supabase_responses):
    calc = LTRSubCalculatorKosztyDodatkowe(
        okres_uzytkowania=36,
        przebieg=60000,
        czy_gps=True,
        is_demontaz=False,
        hak=False,
        klasa_pojazdu="C",
        klasa_id=1,
        typ_zabudowy=None,
    )
    # GSM uses static 39 + 120(price)/6 * 3 + 120(montaz) -> (39 * 36) + (20 * 3) + 120
    # Wait, months = 36. 120/6 * 36/12 = 20 * 3 = 60.
    # Total = 1404 + 60 + 120 = 1584
    cost = calc._get_abonament_gsm()
    assert cost == 1584.0

    calc.czy_gps = False
    assert calc._get_abonament_gsm() == 0.0


def test_koszty_dodatkowe_zabudowy(mock_supabase_responses):
    calc = LTRSubCalculatorKosztyDodatkowe(
        okres_uzytkowania=24,
        przebieg=60000,
        czy_gps=False,
        is_demontaz=False,
        hak=False,
        klasa_pojazdu="C",
        klasa_id=1,
        typ_zabudowy="Chlodnia",
    )
    # 24/12 * 1000 = 2000
    assert calc._get_koszty_dodatkowe_zabudowy() == 2000.0


def test_korekta_ltr_przygotowanie(mock_supabase_responses):
    calc = LTRSubCalculatorKosztyDodatkowe(
        okres_uzytkowania=36,
        przebieg=60000,
        czy_gps=False,
        is_demontaz=False,
        hak=False,
        klasa_pojazdu="C",
        klasa_id=1,
        typ_zabudowy=None,
        linia_produktowa="LTR",
    )
    # 1.2 * 0.8 * 120 = 0.96 * 120 = 115.2
    assert round(calc._calculate_przygotowanie_do_sprzedazy(), 2) == 115.2


def test_racmtr_przygotowanie(mock_supabase_responses):
    calc = LTRSubCalculatorKosztyDodatkowe(
        okres_uzytkowania=36,
        przebieg=60000,
        czy_gps=False,
        is_demontaz=False,
        hak=False,
        klasa_pojazdu="C",
        klasa_id=1,
        typ_zabudowy=None,
        linia_produktowa="RacMTR",
    )
    assert calc._calculate_przygotowanie_do_sprzedazy() == 120.0


def test_override_przygotowanie(mock_supabase_responses):
    calc = LTRSubCalculatorKosztyDodatkowe(
        okres_uzytkowania=36,
        przebieg=60000,
        czy_gps=False,
        is_demontaz=False,
        hak=False,
        klasa_pojazdu="C",
        klasa_id=1,
        typ_zabudowy=None,
        linia_produktowa="RacMTR",
        korekta_kosztu_przygotowania=True,
        koszt_przygotowania_korekta=60.0,  # Będzie brutto zdejmujemy mockowany VAT=120
    )
    assert calc._calculate_przygotowanie_do_sprzedazy() == 120.0 + (60.0 / 120.0)


def test_calculate_cost_total(mock_supabase_responses):
    calc = LTRSubCalculatorKosztyDodatkowe(
        okres_uzytkowania=36,
        przebieg=60000,
        czy_gps=True,
        is_demontaz=True,
        hak=True,
        klasa_pojazdu="C",
        klasa_id=2,
        typ_zabudowy="Plandeka",
        linia_produktowa="LTR",
    )
    # GSM: 1584
    # Przygotowanie LTR: 115.2
    # Zabudowa: 36/12 * 1000 = 3000
    # Hak: 120 (mock Parametr)
    # Plandeka: 120 (mock WymontowaniaKarty to DemontazKraty) -> 120
    # Rejestracja: 120
    # Ryczalty: 0
    # Total = 1584 + 115.2 + 3000 + 120 + 120 + 120 = 5059.2

    result = calc.calculate_cost()
    assert round(result["total_koszty_dodatkowe_netto"], 2) == 5059.2
    assert result["hak_holowniczy"] == 120.0
    assert result["demontaz_kraty"] == 120.0
    assert result["abonament_gsm"] == 1584.0
    assert result["koszty_zabudowy"] == 3000.0
    assert result["elementy_ryczaltowe"] == 0.0

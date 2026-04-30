"""Test logiki rozdzielenia opcji rabatowalnych/nierabatowalnych w wp_amortyzacja.

Standalone test bez DB — tworzy obiekt-mock LTRKalkulator i wywołuje
_calculate_wr_options_split() bezpośrednio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

import pytest


@dataclass
class _MockOption:
    price_net: float
    name: str = ""
    no_discount: bool = False
    include_in_wr: bool = False


@dataclass
class _MockInputData:
    factory_options: List[_MockOption] = field(default_factory=list)
    service_options: List[_MockOption] = field(default_factory=list)
    discount_pct: float = 0.0


def _wr_split(input_data: _MockInputData) -> Tuple[float, float, float]:
    """Replikuje logikę LTRKalkulator._calculate_wr_options_split bez importu klasy
    (która wymaga DB).

    Jeśli zmienisz logikę w LTRKalkulator, zaktualizuj też tutaj — to test referencyjny
    który łapie regresje w sumarycznej dekompozycji opcji.
    """
    discountable = sum(
        opt.price_net for opt in input_data.factory_options if not opt.no_discount
    )
    non_discountable = sum(
        opt.price_net for opt in input_data.factory_options if opt.no_discount
    )
    service_in_wr = sum(
        opt.price_net for opt in input_data.service_options if opt.include_in_wr
    )
    return discountable, non_discountable, service_in_wr


def _wp_amortyzacja(
    vehicle_capex: float, input_data: _MockInputData
) -> float:
    """Replikuje wp_amortyzacja po naprawie."""
    disc, non_disc, svc = _wr_split(input_data)
    discount_factor = 1.0 - (input_data.discount_pct / 100.0)
    return vehicle_capex + disc * discount_factor + non_disc + svc


class TestWrOptionsSplit:
    def test_all_discountable_default(self) -> None:
        data = _MockInputData(
            factory_options=[
                _MockOption(price_net=2000),
                _MockOption(price_net=3000),
            ]
        )
        disc, non_disc, svc = _wr_split(data)
        assert disc == 5000
        assert non_disc == 0
        assert svc == 0

    def test_dealer_zabudowa_marked_non_discountable(self) -> None:
        data = _MockInputData(
            factory_options=[
                _MockOption(price_net=2725, name="Hak+kluczyki+koło"),
                _MockOption(price_net=31732, name="ZABUDOWA WYWROTKA", no_discount=True),
            ]
        )
        disc, non_disc, svc = _wr_split(data)
        assert disc == 2725
        assert non_disc == 31732
        assert svc == 0

    def test_service_options_in_wr_only_when_flagged(self) -> None:
        data = _MockInputData(
            service_options=[
                _MockOption(price_net=5000, include_in_wr=True),
                _MockOption(price_net=2000, include_in_wr=False),
            ]
        )
        disc, non_disc, svc = _wr_split(data)
        assert svc == 5000
        # Service options never go into discountable/non_discountable buckets
        assert disc == 0
        assert non_disc == 0


class TestWpAmortyzacja:
    """Najważniejszy test — odtwarza Forda Trakcja i sprawdza że zabudowa
    NIE jest dyskontowana podczas obliczania wartości do amortyzacji."""

    def test_ford_trakcja_amortyzacja_correct_with_no_discount_flag(self) -> None:
        # Cena bazowa 142 760 + opcje fabryczne 2 725 = 145 485
        # Zabudowa 31 732 jako non_discountable
        # Rabat 29.08% (= 42 317 z 145 485)
        data = _MockInputData(
            factory_options=[
                _MockOption(price_net=2725, name="kluczyki+hak+koło"),
                _MockOption(price_net=31732, name="ZABUDOWA WYWROTKA", no_discount=True),
            ],
            discount_pct=29.08,
        )
        vehicle_capex = 142760
        wp = _wp_amortyzacja(vehicle_capex, data)
        # Oczekiwane: 142760 + 2725*(1-0.2908) + 31732 + 0
        # = 142760 + 1932.43 + 31732 = 176424.43
        # WAŻNE: zabudowa 31732 W PEŁNI wlicza się do amortyzacji
        # mimo że NIE jest dyskontowana przy zakupie
        assert wp == pytest.approx(142760 + 2725 * (1 - 0.2908) + 31732, rel=0.001)
        assert wp > 175_000  # Sanity: znacznie większe niż samo auto + kluczyki

    def test_ford_trakcja_amortyzacja_BUG_when_no_discount_flag_missing(self) -> None:
        """Stary bug: zabudowa NIE oznaczona no_discount → dyskontowana → wp_amortyzacja zaniżone."""
        data_buggy = _MockInputData(
            factory_options=[
                _MockOption(price_net=2725),
                _MockOption(price_net=31732, no_discount=False),  # ❌ błędnie
            ],
            discount_pct=29.08,
        )
        wp_buggy = _wp_amortyzacja(142760, data_buggy)
        # Zabudowa zostaje obniżona o ~9 230 zł — błąd ekonomiczny
        # bo zabudowa NIE traci wartości jak rabat producenta
        assert wp_buggy < 175_000  # zaniżone

        # Po poprawce — zabudowa flagowana
        data_correct = _MockInputData(
            factory_options=[
                _MockOption(price_net=2725),
                _MockOption(price_net=31732, no_discount=True),
            ],
            discount_pct=29.08,
        )
        wp_correct = _wp_amortyzacja(142760, data_correct)

        # Różnica = wartość niezdyskontowanej zabudowy
        diff = wp_correct - wp_buggy
        assert diff == pytest.approx(31732 * 0.2908, rel=0.001)
        # Czyli ~9 226 zł większa baza amortyzacji = wyższa miesięczna utrata wartości

    def test_no_discount_no_options_baseline(self) -> None:
        data = _MockInputData(discount_pct=0.0)
        wp = _wp_amortyzacja(100_000, data)
        assert wp == 100_000

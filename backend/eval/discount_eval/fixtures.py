"""Ground truth dla 14 ofert Ford Trakcja (sporzadzone 2026-03-31 do 2026-04-02).

Liczby zostaly wyekstrahowane regexem z sekcji 'PODSUMOWANIE OFERTY' kazdego PDF-a
i triangulowane: shown - rabat + non_discountable = total.

Te wartosci sa REFERENCJA do ktorej porownujemy wynik `derive_discount_breakdown`.
Jesli ktorys PDF ma inne dane (np. nowsza wersja), zaktualizuj wartosc tutaj.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiscountFixture:
    """Referencyjne dane jednej oferty."""

    file_name: str
    base_price: float
    factory_options_price: float
    cena_prezentowanego_modelu: float  # = base + factory
    rabat_pln: float
    cena_z_rabatem: float
    expected_non_discountable: float
    expected_pct: float

    @property
    def expected_discountable_base(self) -> float:
        return self.cena_prezentowanego_modelu


# 14 fixture'ow z eval_extracted.json (wyekstrahowane przez ekstraktor regexowy z PDF-a)
FIXTURES: list[DiscountFixture] = [
    DiscountFixture(
        file_name="OFERTA_nr_8924_2026_03_z_dnia_2026-03-31.pdf",
        base_price=164275, factory_options_price=6750,
        cena_prezentowanego_modelu=171025, rabat_pln=42125,
        cena_z_rabatem=128900, expected_non_discountable=0,
        expected_pct=24.63,
    ),
    DiscountFixture(
        file_name="OFERTA_nr_8927_2026_03_z_dnia_2026-03-31.pdf",
        base_price=164275, factory_options_price=7250,
        cena_prezentowanego_modelu=171525, rabat_pln=42125,
        cena_z_rabatem=129400, expected_non_discountable=0,
        expected_pct=24.56,
    ),
    DiscountFixture(
        file_name="OFERTA_nr_8963_2026_04_z_dnia_2026-04-01.pdf",
        base_price=146595, factory_options_price=5560,
        cena_prezentowanego_modelu=152155, rabat_pln=43755,
        cena_z_rabatem=108400, expected_non_discountable=0,
        expected_pct=28.76,
    ),
    DiscountFixture(
        file_name="OFERTA_nr_8964_2026_04_z_dnia_2026-04-01.pdf",
        base_price=154595, factory_options_price=5560,
        cena_prezentowanego_modelu=160155, rabat_pln=39955,
        cena_z_rabatem=120200, expected_non_discountable=0,
        expected_pct=24.95,
    ),
    DiscountFixture(
        file_name="OFERTA_nr_8965_2026_04_z_dnia_2026-04-01.pdf",
        base_price=157890, factory_options_price=4960,
        cena_prezentowanego_modelu=162850, rabat_pln=30550,
        cena_z_rabatem=132300, expected_non_discountable=0,
        expected_pct=18.76,
    ),
    DiscountFixture(
        file_name="OFERTA_nr_8966_2026_04_z_dnia_2026-04-01.pdf",
        base_price=165890, factory_options_price=4960,
        cena_prezentowanego_modelu=170850, rabat_pln=31860,
        cena_z_rabatem=138990, expected_non_discountable=0,
        expected_pct=18.65,
    ),
    DiscountFixture(
        file_name="OFERTA_nr_9003_2026_04_z_dnia_2026-04-01.pdf",
        base_price=109975, factory_options_price=1890,
        cena_prezentowanego_modelu=111865, rabat_pln=22720,
        cena_z_rabatem=91850, expected_non_discountable=2705,
        expected_pct=20.31,
    ),
    DiscountFixture(
        file_name="OFERTA_nr_9032_2026_04_z_dnia_2026-04-01.pdf",
        base_price=199990, factory_options_price=5600,
        cena_prezentowanego_modelu=205590, rabat_pln=51090,
        cena_z_rabatem=154500, expected_non_discountable=0,
        expected_pct=24.85,
    ),
    DiscountFixture(
        file_name="OFERTA_nr_9138_2026_04_z_dnia_2026-04-02.pdf",
        base_price=138260, factory_options_price=8700,
        cena_prezentowanego_modelu=146960, rabat_pln=40761,
        cena_z_rabatem=123600, expected_non_discountable=17401,
        expected_pct=27.74,
    ),
    DiscountFixture(
        file_name="OFERTA_nr_9139_2026_04_z_dnia_2026-04-02.pdf",
        base_price=138260, factory_options_price=9325,
        cena_prezentowanego_modelu=147585, rabat_pln=42585,
        cena_z_rabatem=125400, expected_non_discountable=20400,
        expected_pct=28.85,
    ),
    # ★ Wzorcowy case Forda Trakcja z zabudowa typu wywrotka
    DiscountFixture(
        file_name="OFERTA_nr_9142_2026_04_z_dnia_2026-04-02.pdf",
        base_price=142760, factory_options_price=2725,
        cena_prezentowanego_modelu=145485, rabat_pln=42317,
        cena_z_rabatem=134900, expected_non_discountable=31732,
        expected_pct=29.09,
    ),
    DiscountFixture(
        file_name="OFERTA_nr_9153_2026_04_z_dnia_2026-04-02.pdf",
        base_price=142760, factory_options_price=2725,
        cena_prezentowanego_modelu=145485, rabat_pln=42071,
        cena_z_rabatem=121500, expected_non_discountable=18086,
        expected_pct=28.92,
    ),
    DiscountFixture(
        file_name="OFERTA_nr_9155_2026_04_z_dnia_2026-04-02.pdf",
        base_price=142760, factory_options_price=2725,
        cena_prezentowanego_modelu=145485, rabat_pln=42061,
        cena_z_rabatem=120160, expected_non_discountable=16736,
        expected_pct=28.91,
    ),
    DiscountFixture(
        file_name="OFERTA_nr_9166_2026_04_z_dnia_2026-04-02.pdf",
        base_price=181200, factory_options_price=5175,
        cena_prezentowanego_modelu=186375, rabat_pln=54075,
        cena_z_rabatem=150200, expected_non_discountable=17900,
        expected_pct=29.01,
    ),
]

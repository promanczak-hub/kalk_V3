"""Pipeline input resolvers (Control Center + CalculatorInput).

Single source of truth dla rozstrzygania, skąd brać wartość pipeline'u
LTR. Używane przez `ltr_cell_calculator` oraz `PipelineDebugger`, żeby
obie ścieżki kalkulacji dawały **identyczne** wyniki.

Reguły (per memory `feedback_no_calc_fallbacks` + CLAUDE.md anti-patterns):

* `_resolve_finance_rate` — input override → settings → raise.
* `_require_setting`     — settings → raise (brak override z inputu).

Bez literal defaults (`5.0`, `2.0`, `1.23`, `0.0`). Brak wartości w
Control Center = operacyjny błąd konfiguracji, **nie** dopuszczamy do
silent fallbacku przy generowaniu transakcyjnej oferty.
"""
from __future__ import annotations

from typing import Any


def _resolve_finance_rate(
    input_field: str,
    input_data: Any,
    settings: Any,
    settings_attr: str,
) -> float:
    """Resolve a percentage finance input (WIBOR or bank margin).

    Priorytet:
      1. `input_data.<input_field>` jeśli != None (override z UI / API).
      2. `settings.<settings_attr>` jeśli != None (Control Center SOT).
      3. `ValueError` — nie ma literal-default jak `5.0` czy `2.0`.

    `float()` wybuchnie naturalnie na bezsensownym typie — nie tłumimy.
    """
    override = getattr(input_data, input_field, None)
    if override is not None:
        return float(override)

    cc_value = getattr(settings, settings_attr, None)
    if cc_value is not None:
        return float(cc_value)

    raise ValueError(
        f"Brak parametru finansowego '{input_field}' w CalculatorInput "
        f"oraz '{settings_attr}' w Control Center. "
        f"Pipeline LTR wymaga obu źródeł — fail-fast (per `feedback_no_calc_fallbacks`)."
    )


def _require_setting(settings: Any, attr: str, label: str | None = None) -> Any:
    """Zwróć `settings.<attr>` lub rzuć `ValueError`.

    Używać dla parametrów Control Center wpływających na pipeline kalkulacji
    (VAT, ubezpieczenie, GSM CAPEX, normatywny przebieg, budżet marketingowy).
    Brak danych = błąd konfiguracji CC, NIE silent fallback do literala.
    """
    value = getattr(settings, attr, None)
    if value is None:
        what = label or attr
        raise ValueError(
            f"Brak parametru '{what}' (settings.{attr}) w Control Center. "
            f"Pipeline LTR wymaga jawnej wartości — fail-fast "
            f"(per `feedback_no_calc_fallbacks`)."
        )
    return value

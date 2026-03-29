"""HTML report builder for LTR matrix cells."""
from __future__ import annotations

from html import escape
from typing import Any, Dict


def _fmt(val: Any) -> str:
    if isinstance(val, (int, float)):
        return f"{val:,.2f}".replace(",", " ").replace(".", ",")
    return str(val or "-")


def to_koszt_dict(k_item: Any) -> Dict[str, Any]:
    return {
        "RozkladMarzy": k_item.rozklad_marzy,
        "RozkladMarzyKorekta": k_item.rozklad_marzy_korekta,
        "KwotaMarzy": round(k_item.kwota_marzy, 0),
        "KwotaMarzyKorekta": round(k_item.kwota_marzy_korekta, 0),
        "KosztPlusMarza": round(k_item.koszt_plus_marza, 0),
        "KosztPlusMarzaKorekta": round(k_item.koszt_plus_marza_korekta, 0),
    }


def build_report_html(cell: Dict[str, Any]) -> str:
    rows = [
        ("Okres (mc)", _fmt(cell.get("Okres"))),
        ("Przebieg (km/rok)", _fmt(cell.get("Przebieg"))),
        ("Stawka laczna", _fmt(cell.get("LacznaStawka"))),
        ("Czynsz finansowy", _fmt(cell.get("CzynszFinansowy"))),
        ("Czynsz techniczny", _fmt(cell.get("CzynszTechniczny"))),
        ("WR", _fmt(cell.get("WR"))),
        ("Utrata wartosci", _fmt(cell.get("UtrataWartosci"))),
        ("Cena zakupu", _fmt(cell.get("CenaZakupu"))),
        ("Koszty dodatkowe", _fmt(cell.get("KosztyDodatkowe"))),
        ("Ubezpieczenie", _fmt(cell.get("LacznieUbezpieczenie"))),
        ("Serwis", _fmt(cell.get("KosztySerwisowe"))),
        ("Opony", _fmt(cell.get("LacznyKosztOpon"))),
        ("Samochod zastepczy", _fmt(cell.get("LacznieSamochodZastepczy"))),
        ("Marza miesiac", _fmt(cell.get("MarzaMiesiac"))),
        ("Marza na kontrakcie", _fmt(cell.get("MarzaNaKontrakcie"))),
        ("Koszt dzienny", _fmt(cell.get("KosztDzienny"))),
    ]

    row_html = "".join(
        f"<tr><td>{escape(label)}</td><td class='val'>{escape(value)}</td></tr>"
        for label, value in rows
    )

    return (
        "<!doctype html><html><head><meta charset='utf-8'/>"
        "<style>"
        "body{font-family:Segoe UI,Arial,sans-serif;background:#fff;color:#0f172a;margin:16px;}"
        "h3{margin:0 0 10px 0;font-size:16px;}"
        "table{border-collapse:collapse;width:100%;font-size:12px;}"
        "td{border:1px solid #cbd5e1;padding:6px 8px;vertical-align:top;}"
        "td.val{text-align:right;font-weight:600;white-space:nowrap;}"
        "</style></head><body>"
        f"<h3>Karta kalkulacji (V3)</h3><table>{row_html}</table>"
        "</body></html>"
    )

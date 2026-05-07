"""Generator XLSX oferty LTR — multi-sheet layout.

Główny arkusz "Oferta" zawiera tabelę pojazdów z hyperlinkami do dedykowanych
arkuszy per pojazd (po jednym na kalkulację). Każdy arkusz pojazdu ma sekcje:
Pojazd / Warunki finansowania / W cenie raty / Wyposażenie standardowe oraz
dolne sekcje Notatki + Opcje fabryczne/dealerskie z cenami.
"""
import io
import logging
from datetime import datetime, timedelta
from typing import Any

from openpyxl import Workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

logger = logging.getLogger(__name__)


NAVY = "003366"
WHITE = "FFFFFF"
SOFT_BLUE = "E8F1F8"
YELLOW = "FFF8DC"
GRAY = "555555"
DARK_GRAY = "333333"
ZEBRA = "F5F9FC"
LINK_BLUE = "0563C1"
GREEN_OK = "2E7D32"
RED_NO = "C62828"
RED_BG = "FFC7CE"  # Excel "Bad" light red — used for missing fin/tech split
RED_BORDER = "C00000"

# Mirror of frontend OVERUSE_FEE_OPTIONS (OfferCartDrawer.tsx) — values shown
# in the dropdown on column M in the main sheet. 71 values, 0.10..0.80 step 0.01.
OVERUSE_FEE_OPTIONS: list[float] = [round(0.10 + i * 0.01, 2) for i in range(71)]
_OVERUSE_HELPER_SHEET = "_overuse_options"

_INVALID_SHEET_CHARS = set(":\\/?*[]")


def _thin_border(color: str = "CCCCCC") -> Border:
    s = Side(style="thin", color=color)
    return Border(left=s, right=s, top=s, bottom=s)


def _safe_sheet_name(raw: str, taken: set[str]) -> str:
    """Sanitise to a valid Excel sheet name (≤31 chars, unique within workbook)."""
    cleaned = "".join("-" if c in _INVALID_SHEET_CHARS else c for c in (raw or "Pojazd"))
    cleaned = cleaned.strip() or "Pojazd"
    base = cleaned[:31]
    candidate = base
    suffix = 2
    while candidate in taken:
        tail = f"-{suffix}"
        candidate = (base[: 31 - len(tail)]) + tail
        suffix += 1
    taken.add(candidate)
    return candidate


def _format_pln_int(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{int(round(float(value))):,}".replace(",", " ") + " zł"


def _format_pln_dec(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{float(value):,.2f}".replace(",", " ").replace(".", ",") + " zł"


def _format_int(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{int(round(float(value))):,}".replace(",", " ")


class ExcelOfferGenerator:
    """Generates the multi-sheet XLSX offer from enriched OfferItem dicts."""

    SLOGAN = "Express | Kieruj się wygodą !"
    COMPANY_LINE = (
        "Express Sp. z o.o. Sp.k. | ul. Puszkarska 7F, 30-644 Kraków | www.express.pl"
    )

    def __init__(self) -> None:
        self.now = datetime.now()
        self.valid_until = self.now + timedelta(days=30)

    def generate_offer(
        self,
        client_name: str,
        client_nip: str,
        items: list[dict[str, Any]],
        client_address: str = "",
        representative: str = "",
    ) -> bytes:
        wb = Workbook()
        wb.remove(wb.active)  # type: ignore[arg-type]

        taken_sheet_names: set[str] = set()
        for item in items:
            item["_sheet_name"] = _safe_sheet_name(
                item.get("sheet_label") or item.get("kalk_numer") or item.get("id") or "Pojazd",
                taken_sheet_names,
            )

        self._write_main_sheet(wb, items, client_name, client_nip, client_address, representative)
        for item in items:
            self._write_vehicle_sheet(wb, item)

        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        return out.read()

    # ───────────────────────────── main sheet ─────────────────────────────
    def _write_main_sheet(
        self,
        wb: Workbook,
        items: list[dict[str, Any]],
        client_name: str,
        client_nip: str,
        client_address: str,
        representative: str,
    ) -> None:
        ws = wb.create_sheet("Oferta", 0)

        ws.merge_cells("A1:F1")
        ws["A1"] = self.COMPANY_LINE
        ws["A1"].font = Font(name="Calibri", size=10, color=GRAY)
        ws["A1"].alignment = Alignment(vertical="center", horizontal="left")

        ws.merge_cells("J1:N1")
        ws["J1"] = self.SLOGAN
        ws["J1"].font = Font(name="Calibri", size=18, bold=True, color=NAVY)
        ws["J1"].alignment = Alignment(vertical="center", horizontal="right")
        ws.row_dimensions[1].height = 65

        ws.row_dimensions[2].height = 0.75
        ws.row_dimensions[3].height = 0.75

        ws.merge_cells("A4:N4")
        ws["A4"] = "OFERTA NAJMU DŁUGOTERMINOWEGO"
        ws["A4"].font = Font(name="Calibri", size=16, bold=True, color=NAVY)
        ws["A4"].alignment = Alignment(vertical="center", horizontal="center")
        ws.row_dimensions[4].height = 30

        ws.merge_cells("A5:E5")
        ws["A5"] = f"Data sporządzenia oferty: {self.now:%Y-%m-%d}"
        ws["A5"].font = Font(name="Calibri", size=10, color=DARK_GRAY)
        ws.merge_cells("F5:N5")
        ws["F5"] = f"Data ważności oferty: {self.valid_until:%Y-%m-%d}"
        ws["F5"].font = Font(name="Calibri", size=11, color=DARK_GRAY)
        ws["F5"].alignment = Alignment(horizontal="right")

        ws.row_dimensions[6].height = 5

        client_block = f"Oferta przygotowana dla:\n{client_name}\nNIP: {client_nip}"
        if client_address:
            client_block += f"\n{client_address}"
        ws.merge_cells("A7:F8")
        ws["A7"] = client_block
        ws["A7"].font = Font(name="Calibri", size=10, bold=True, color=NAVY)
        ws["A7"].fill = PatternFill("solid", fgColor=SOFT_BLUE)
        ws["A7"].alignment = Alignment(vertical="center", wrap_text=True, indent=1)

        prep_block = f"Oferta przygotowana przez:\n{representative or 'Express LTR'}"
        ws.merge_cells("G7:N8")
        ws["G7"] = prep_block
        ws["G7"].font = Font(name="Calibri", size=10, bold=True, color=NAVY)
        ws["G7"].fill = PatternFill("solid", fgColor=SOFT_BLUE)
        ws["G7"].alignment = Alignment(vertical="center", wrap_text=True, indent=1)
        ws.row_dimensions[7].height = 32
        ws.row_dimensions[8].height = 32

        ws.row_dimensions[9].height = 10

        # Headers row 10 — column N (Rodzaj kosztów) widened to fit a list of
        # active categories (e.g. "Serwis ASO • Opony (Medium) • OC/AC"); new
        # column O holds tire class + set count.
        headers = [
            ("A", "↗", 4),
            ("B", "Numer kalk.\nVIN\nKonfiguracja", 22),
            ("C", "Model", 38),
            ("D", "Cena katalogowa\nnetto", 14),
            ("E", "Cena opcji\nfabrycznych netto", 13),
            ("F", "Cena opcji\nserwisowych netto", 13),
            ("G", "Okres\numowny", 9),
            ("H", "Limit km\nkontrakt / rok", 14),
            ("I", "Czynsz\ninicjalny netto", 11),
            ("J", "Łączny czynsz\nnetto (K+L)", 14),
            ("K", "Część\nfinansowa", 11),
            ("L", "Część\ntechniczna", 11),
            ("M", "Opłata za\nnadprzebieg", 12),
            ("N", "Rodzaj kosztów", 28),
            ("O", "Ogumienie\n(klasa • ilość)", 22),
        ]
        for col, label, width in headers:
            ws.column_dimensions[col].width = width
            c = ws[f"{col}10"]
            c.value = label
            c.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
            c.fill = PatternFill("solid", fgColor=NAVY)
            c.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
            c.border = _thin_border(NAVY)
        ws.row_dimensions[10].height = 40

        red_border = Border(
            left=Side(style="thin", color=RED_BORDER),
            right=Side(style="thin", color=RED_BORDER),
            top=Side(style="thin", color=RED_BORDER),
            bottom=Side(style="thin", color=RED_BORDER),
        )

        for i, item in enumerate(items):
            row = 11 + i
            zebra = ZEBRA if i % 2 == 1 else WHITE
            sheet_name = item["_sheet_name"]

            a = ws.cell(row=row, column=1, value="↗")
            a.hyperlink = f"#'{sheet_name}'!A1"
            a.font = Font(name="Calibri", size=14, bold=True, color=LINK_BLUE, underline="single")
            a.alignment = Alignment(vertical="center", horizontal="center")
            a.fill = PatternFill("solid", fgColor=zebra)

            kalk_numer = item.get("kalk_numer") or "—"
            vin = item.get("vin") or "—"
            cfg = item.get("config_code") or item.get("offer_number") or "—"
            # Rich text: kalk_numer prominent (bold NAVY 11pt), VIN/Konf small grey.
            kalk_font = InlineFont(rFont="Calibri", sz=11, b=True, color=NAVY)
            sub_font = InlineFont(rFont="Calibri", sz=9, color=DARK_GRAY)
            b = ws.cell(row=row, column=2)
            b.value = CellRichText(
                TextBlock(kalk_font, str(kalk_numer)),
                TextBlock(sub_font, f"\nVIN: {vin}\nKonf: {cfg}"),
            )
            b.alignment = Alignment(vertical="center", wrap_text=True, indent=1)
            b.fill = PatternFill("solid", fgColor=zebra)

            c = ws.cell(row=row, column=3, value=item.get("marketing_name") or "—")
            c.font = Font(name="Calibri", size=11, bold=True)
            c.alignment = Alignment(vertical="center", wrap_text=True, indent=1)
            c.fill = PatternFill("solid", fgColor=zebra)

            ws.cell(row=row, column=4, value=item.get("base_price_net") or 0)
            ws.cell(row=row, column=5, value=item.get("factory_options_total") or 0)
            ws.cell(row=row, column=6, value=item.get("service_options_total") or 0)
            ws.cell(row=row, column=7, value=f"{item.get('term') or 0} miesięcy")

            # Limit km — kontraktowy jako główna liczba, roczny jako podtytuł.
            # Klient B2B porównuje oferty po sumarycznym limicie (cap nadprzebiegu),
            # ale potrzebuje też zobaczyć roczne tempo.
            annual_km = int(item.get("mileage") or 0)
            term_months_h = int(item.get("term") or 0)
            contract_km = (
                int(round(annual_km * term_months_h / 12))
                if annual_km and term_months_h
                else 0
            )
            h_cell = ws.cell(row=row, column=8)
            contract_label = f"{contract_km:,}".replace(",", " ") + " km" if contract_km else "—"
            annual_label = f"{annual_km:,}".replace(",", " ") + " / rok" if annual_km else "—"
            h_cell.value = CellRichText(
                TextBlock(InlineFont(rFont="Calibri", sz=11, b=True), contract_label),
                TextBlock(InlineFont(rFont="Calibri", sz=8, color=GRAY), f"\n{annual_label}"),
            )

            ws.cell(row=row, column=9, value=item.get("contribution") or 0)

            financial = item.get("financial")
            technical = item.get("technical")
            split_missing = financial is None or technical is None
            rata = ws.cell(row=row, column=10)
            k_cell = ws.cell(row=row, column=11)
            l_cell = ws.cell(row=row, column=12)
            if split_missing:
                # Recompute failed — leave K, L, J empty and flag in red. Don't
                # invent numbers that the customer might quote back to us.
                rata.value = None
                k_cell.value = None
                l_cell.value = None
                logger.warning(
                    "fin/tech split missing for kalk_numer=%s — K/L/J left blank",
                    item.get("kalk_numer") or item.get("id") or "?",
                )
                _comment = Comment(
                    "Brak podziału finansowo-technicznego dla tej kalkulacji.",
                    "system",
                )
                k_cell.comment = _comment
                l_cell.comment = Comment(
                    "Brak podziału finansowo-technicznego dla tej kalkulacji.",
                    "system",
                )
            else:
                k_cell.value = financial
                l_cell.value = technical
                # Łączny czynsz wyrażony formułą — wymusza spójność z K i L,
                # nawet jeśli ktoś ręcznie zmieni jedną z tych wartości.
                rata.value = f"=K{row}+L{row}"

            ws.cell(row=row, column=13, value=item.get("overuse_fee") or 0.50)
            ws.cell(row=row, column=14, value=item.get("cost_breakdown") or item.get("cost_type") or "—")
            ws.cell(row=row, column=15, value=item.get("tire_display") or "—")

            for col_idx in range(4, 16):
                cell = ws.cell(row=row, column=col_idx)
                cell.alignment = Alignment(vertical="center", horizontal="center")
                cell.fill = PatternFill("solid", fgColor=zebra)
                if col_idx == 8:
                    # Rich-text already has its own fonts (contract km bold,
                    # annual km small grey) — don't override; just enable wrap.
                    cell.alignment = Alignment(
                        vertical="center", horizontal="center", wrap_text=True
                    )
                    continue
                cell.font = Font(name="Calibri", size=11)
                if col_idx in (4, 5, 6, 9, 10, 11, 12):
                    cell.number_format = '#,##0 "zł"'
                elif col_idx == 13:
                    cell.number_format = '0.00 "zł/km"'
                elif col_idx in (14, 15):
                    cell.alignment = Alignment(
                        vertical="center", horizontal="left", wrap_text=True, indent=1
                    )
                    cell.font = Font(name="Calibri", size=9)

            rata.font = Font(name="Calibri", size=12, bold=True, color=NAVY)
            rata.fill = PatternFill("solid", fgColor=YELLOW)

            for col_idx in range(1, 16):
                ws.cell(row=row, column=col_idx).border = _thin_border()

            if split_missing:
                red_fill = PatternFill("solid", fgColor=RED_BG)
                for col_idx in (10, 11, 12):
                    cell = ws.cell(row=row, column=col_idx)
                    cell.fill = red_fill
                    cell.border = red_border

            ws.row_dimensions[row].height = 50

        # Freeze header row (no autofilter — those dropdowns confuse users).
        last_row = 10 + len(items)
        ws.freeze_panes = "A11"

        if items:
            self._add_overuse_validation(wb, ws, last_row)

        # Footer
        footer_row = last_row + 2
        ws.cell(row=footer_row, column=1, value="Informacje dodatkowe:").font = Font(
            name="Calibri", size=10, bold=True, color=GRAY
        )
        ws.merge_cells(start_row=footer_row + 1, start_column=1, end_row=footer_row + 1, end_column=15)
        foot = ws.cell(row=footer_row + 1, column=1)
        foot.value = (
            "1) Wszystkie ceny podane w kalkulacji są cenami netto.\n"
            "2) Oferta ważna pod warunkiem akceptacji klienta przed datą wygaśnięcia.\n"
            "3) Kliknij ikonę ↗ przy danym pojeździe, aby zobaczyć pełną specyfikację."
        )
        foot.font = Font(name="Calibri", size=9, color=GRAY)
        foot.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[footer_row + 1].height = 50

        ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_options.horizontalCentered = True
        ws.page_margins = ws.page_margins.__class__(left=0.3, right=0.3, top=0.4, bottom=0.4)

    # ───────────────────────────── helpers ─────────────────────────────
    def _add_overuse_validation(self, wb: Workbook, ws, last_row: int) -> None:
        """Attach a list-style data validation to column M (overuse fee) on rows
        11..last_row. The dropdown values come from a hidden helper sheet so we
        avoid openpyxl's 255-char limit on inline list formulas (71 values × ~5
        chars ≈ 355 chars)."""
        helper = wb.create_sheet(_OVERUSE_HELPER_SHEET)
        for idx, value in enumerate(OVERUSE_FEE_OPTIONS, start=1):
            helper.cell(row=idx, column=1, value=value).number_format = "0.00"
        helper.column_dimensions["A"].width = 8
        helper.sheet_state = "hidden"

        formula = f"={_OVERUSE_HELPER_SHEET}!$A$1:$A${len(OVERUSE_FEE_OPTIONS)}"
        dv = DataValidation(type="list", formula1=formula, allow_blank=False)
        dv.error = "Wybierz wartość z listy 0.10–0.80 zł/km"
        dv.errorTitle = "Niepoprawna stawka"
        dv.prompt = "Stawka za każdy km ponad limit"
        dv.promptTitle = "Opłata za nadprzebieg"
        dv.showErrorMessage = True
        ws.add_data_validation(dv)
        dv.add(f"M11:M{last_row}")

    # ───────────────────────────── per-vehicle sheet ─────────────────────────────
    def _write_vehicle_sheet(self, wb: Workbook, item: dict[str, Any]) -> None:
        ws = wb.create_sheet(item["_sheet_name"])

        widths = {
            "A": 20, "B": 22, "C": 3,
            "D": 22, "E": 20, "F": 3,
            "G": 20, "H": 32, "I": 3,
            "J": 18, "K": 26, "L": 3,
        }
        for col, w in widths.items():
            ws.column_dimensions[col].width = w

        # Top row: back link, branding, kalk number
        back = ws["A1"]
        back.value = "← Wróć do oferty"
        back.hyperlink = "#Oferta!A1"
        back.font = Font(name="Calibri", size=11, bold=True, color=LINK_BLUE, underline="single")
        back.alignment = Alignment(vertical="center", indent=1)

        ws.merge_cells("D1:H1")
        ws["D1"] = self.SLOGAN
        ws["D1"].font = Font(name="Calibri", size=14, bold=True, color=NAVY)
        ws["D1"].alignment = Alignment(vertical="center", horizontal="center")

        ws.merge_cells("J1:K1")
        ws["J1"] = f"Kalkulacja: {item.get('kalk_numer') or '—'}"
        ws["J1"].font = Font(name="Calibri", size=10, color=GRAY)
        ws["J1"].alignment = Alignment(vertical="center", horizontal="right")
        ws.row_dimensions[1].height = 30
        ws.row_dimensions[2].height = 5

        # Hero
        ws.merge_cells("A3:K3")
        ws["A3"] = item.get("marketing_name") or "—"
        ws["A3"].font = Font(name="Calibri", size=18, bold=True, color=NAVY)
        ws["A3"].alignment = Alignment(vertical="center", horizontal="center")
        ws.row_dimensions[3].height = 32

        ws.merge_cells("A4:K4")
        rata = item.get("net_installment") or 0
        ws["A4"] = f"Rata miesięczna netto: {_format_pln_int(rata)}"
        ws["A4"].font = Font(name="Calibri", size=14, bold=True, color=NAVY)
        ws["A4"].alignment = Alignment(vertical="center", horizontal="center")
        ws["A4"].fill = PatternFill("solid", fgColor=YELLOW)
        ws.row_dimensions[4].height = 28
        ws.row_dimensions[5].height = 8

        # Section headers row 6
        for rng, label in [
            ("A6:B6", "POJAZD"),
            ("D6:E6", "WARUNKI FINANSOWANIA"),
            ("G6:H6", "W CENIE RATY"),
            ("J6:K6", "WYPOSAŻENIE STANDARDOWE"),
        ]:
            ws.merge_cells(rng)
            c = ws[rng.split(":")[0]]
            c.value = label
            c.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
            c.fill = PatternFill("solid", fgColor=NAVY)
            c.alignment = Alignment(vertical="center", horizontal="center")
        ws.row_dimensions[6].height = 22

        pojazd_rows = [
            ("Marka", item.get("brand") or "—"),
            ("Model", item.get("model") or "—"),
            ("Wersja", item.get("trim") or "—"),
            ("Silnik", f"{int(item['engine_power_hp'])} KM" if item.get("engine_power_hp") else "—"),
            ("Paliwo", item.get("fuel") or "—"),
            ("Skrzynia", item.get("transmission") or "—"),
            ("Napęd", item.get("drive") or "—"),
            ("Typ nadwozia", item.get("body_style") or "—"),
        ]

        term_months = int(item.get("term") or 0)
        annual_mileage = int(item.get("mileage") or 0)
        contract_mileage = int(round(annual_mileage * term_months / 12)) if term_months and annual_mileage else 0
        warunki_rows: list[tuple[str, str]] = [
            ("Okres umowy", f"{term_months} miesięcy"),
            ("Przebieg w kontrakcie", _format_int(contract_mileage) + " km" if contract_mileage else "—"),
            ("Limit km/rok", _format_int(annual_mileage) + " km" if annual_mileage else "—"),
            (
                "Czynsz inicjalny",
                f"{_format_pln_int(item.get('contribution'))}"
                + (f" ({item['contribution_pct']:.1f}%)" if item.get("contribution_pct") else ""),
            ),
            ("Rata miesięczna netto", _format_pln_int(item.get("net_installment"))),
            ("Opłata za nadprzebieg", f"{(item.get('overuse_fee') or 0.50):.2f} zł/km"),
            ("Rodzaj kosztów", item.get("cost_breakdown") or item.get("cost_type") or "—"),
        ]

        ir = item.get("in_rate") or {}
        opony_label_parts = []
        if ir.get("opony"):
            klasa = (ir.get("opony_klasa") or "").strip()
            rozmiar = (ir.get("opony_rozmiar") or "").strip()
            ilosc = ir.get("opony_zestawy")
            if klasa:
                opony_label_parts.append(klasa)
            if rozmiar:
                opony_label_parts.append(rozmiar)
            if ilosc:
                opony_label_parts.append(f"{ilosc} kpl")
        opony_value = " • ".join(opony_label_parts) if opony_label_parts else (True if ir.get("opony") else False)

        in_rate_rows: list[tuple[str, Any]] = [
            ("Ubezpieczenie OC/AC", ir.get("ubezp_oc_ac")),
            ("Serwis", ir.get("serwis_typ") if ir.get("serwis") else False),
            ("Opony", opony_value),
            ("Auto zastępcze", ir.get("auto_zastepcze")),
            ("GPS", ir.get("gps")),
        ]

        standard_items = item.get("standard") or []
        standard_is_placeholder = not bool(standard_items)
        standard_rows = (
            [("— wykaz w PDF konfiguracji —", "")]
            if standard_is_placeholder
            else [(s, "") for s in standard_items]
        )
        max_section_rows = max(
            len(pojazd_rows), len(warunki_rows), len(in_rate_rows), len(standard_rows), 1
        )

        for i in range(max_section_rows):
            r = 7 + i
            zebra = ZEBRA if i % 2 == 0 else WHITE

            if i < len(pojazd_rows):
                self._write_label_value(ws, r, 1, 2, pojazd_rows[i][0], pojazd_rows[i][1], zebra)

            if i < len(warunki_rows):
                label, val = warunki_rows[i]
                la = ws.cell(row=r, column=4, value=label)
                la.font = Font(name="Calibri", size=10, color=GRAY)
                la.alignment = Alignment(vertical="center", indent=1)
                la.fill = PatternFill("solid", fgColor=zebra)
                la.border = _thin_border()
                highlight = label == "Rata miesięczna netto"
                va = ws.cell(row=r, column=5, value=val)
                va.font = Font(
                    name="Calibri",
                    size=11 if highlight else 10,
                    bold=True,
                    color=NAVY if highlight else "000000",
                )
                va.alignment = Alignment(vertical="center", horizontal="right", indent=1)
                va.fill = PatternFill("solid", fgColor=YELLOW if highlight else zebra)
                va.border = _thin_border()

            if i < len(in_rate_rows):
                label, val = in_rate_rows[i]
                la = ws.cell(row=r, column=7, value=label)
                la.font = Font(name="Calibri", size=10, color=GRAY)
                la.alignment = Alignment(vertical="center", indent=1)
                la.fill = PatternFill("solid", fgColor=zebra)
                la.border = _thin_border()
                va = ws.cell(row=r, column=8)
                if val is True or (isinstance(val, str) and val and val not in ("Brak", "—")):
                    va.value = f"✓ {val}" if isinstance(val, str) else "✓"
                    va.font = Font(name="Calibri", size=10, bold=True, color=NAVY)
                else:
                    va.value = "—"
                    va.font = Font(name="Calibri", size=10, color=GRAY)
                va.alignment = Alignment(vertical="center", indent=1, wrap_text=True)
                va.fill = PatternFill("solid", fgColor=zebra)
                va.border = _thin_border()

            if i < len(standard_rows):
                ws.merge_cells(start_row=r, start_column=10, end_row=r, end_column=11)
                if standard_is_placeholder:
                    la = ws.cell(row=r, column=10, value=standard_rows[i][0])
                    la.font = Font(name="Calibri", size=10, italic=True, color=GRAY)
                else:
                    la = ws.cell(row=r, column=10, value=f"•  {standard_rows[i][0]}")
                    la.font = Font(name="Calibri", size=10)
                la.alignment = Alignment(vertical="center", wrap_text=True, indent=1)
                la.fill = PatternFill("solid", fgColor=zebra)
                la.border = _thin_border()

            # Bump row height when the in_rate value (col H) is a long wrapped
            # string (e.g. "Wielosezon Wzmocnione Premium • 4 kpl") so it isn't
            # clipped by the 20pt default.
            row_height = 20
            if i < len(in_rate_rows):
                _, val = in_rate_rows[i]
                if isinstance(val, str) and len(val) > 18:
                    row_height = 32
            ws.row_dimensions[r].height = row_height

        bottom_start = 7 + max_section_rows + 1
        ws.row_dimensions[bottom_start - 1].height = 8

        # NOTATKI band — pełna szerokość, krótkie pole nad opcjami.
        ws.merge_cells(start_row=bottom_start, start_column=1, end_row=bottom_start, end_column=11)
        nh = ws.cell(row=bottom_start, column=1, value="NOTATKI")
        nh.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
        nh.fill = PatternFill("solid", fgColor=NAVY)
        nh.alignment = Alignment(vertical="center", horizontal="center")
        ws.row_dimensions[bottom_start].height = 22

        notes_rows_count = 3
        ws.merge_cells(
            start_row=bottom_start + 1, start_column=1,
            end_row=bottom_start + notes_rows_count, end_column=11,
        )
        nb = ws.cell(row=bottom_start + 1, column=1, value=item.get("notes") or "—")
        nb.font = Font(name="Calibri", size=10, color=DARK_GRAY)
        nb.alignment = Alignment(vertical="top", wrap_text=True, indent=1)
        nb.fill = PatternFill("solid", fgColor=ZEBRA)
        nb.border = _thin_border()
        for nr in range(bottom_start + 1, bottom_start + 1 + notes_rows_count):
            ws.row_dimensions[nr].height = 22

        # OPCJE PŁATNE — pełna szerokość, nazwa A:I, cena netto J, cena brutto K.
        opcje_row = bottom_start + notes_rows_count + 2
        ws.row_dimensions[opcje_row - 1].height = 8
        ws.merge_cells(start_row=opcje_row, start_column=1, end_row=opcje_row, end_column=11)
        oh = ws.cell(row=opcje_row, column=1, value="OPCJE PŁATNE — CENY NETTO / BRUTTO")
        oh.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
        oh.fill = PatternFill("solid", fgColor=NAVY)
        oh.alignment = Alignment(vertical="center", horizontal="center")
        ws.row_dimensions[opcje_row].height = 22

        factory = item.get("factory_options_priced") or []
        dealer = item.get("dealer_options_priced") or []

        def _write_options_block(start_row: int, label: str, rows: list, empty_text: str) -> int:
            """Render one options sub-table (header + data/empty row). Returns
            the next free row number."""
            r_local = start_row
            # Sub-section header row: name in A:I, "cena netto" in J, "cena brutto" in K.
            ws.merge_cells(start_row=r_local, start_column=1, end_row=r_local, end_column=9)
            cell = ws.cell(row=r_local, column=1, value=label)
            cell.font = Font(name="Calibri", size=10, bold=True, color=NAVY)
            cell.alignment = Alignment(vertical="center", indent=1)
            cell.fill = PatternFill("solid", fgColor=SOFT_BLUE)
            net_hdr = ws.cell(row=r_local, column=10, value="cena netto")
            net_hdr.font = Font(name="Calibri", size=10, bold=True, color=NAVY)
            net_hdr.alignment = Alignment(vertical="center", horizontal="right", indent=1)
            net_hdr.fill = PatternFill("solid", fgColor=SOFT_BLUE)
            gross_hdr = ws.cell(row=r_local, column=11, value="cena brutto")
            gross_hdr.font = Font(name="Calibri", size=10, bold=True, color=NAVY)
            gross_hdr.alignment = Alignment(vertical="center", horizontal="right", indent=1)
            gross_hdr.fill = PatternFill("solid", fgColor=SOFT_BLUE)
            r_local += 1

            if rows:
                for entry in rows:
                    # Tolerate legacy 2-tuples (name, net) by deriving gross.
                    if len(entry) == 3:
                        name, net, gross = entry
                    else:
                        name, net = entry
                        gross = round(float(net or 0) * 1.23, 2)
                    ws.merge_cells(start_row=r_local, start_column=1, end_row=r_local, end_column=9)
                    nm = ws.cell(row=r_local, column=1, value=name)
                    nm.font = Font(name="Calibri", size=10)
                    nm.alignment = Alignment(vertical="center", indent=1, wrap_text=True)
                    nm.border = _thin_border()
                    pn = ws.cell(row=r_local, column=10, value=net)
                    pn.font = Font(name="Calibri", size=10)
                    pn.alignment = Alignment(vertical="center", horizontal="right", indent=1)
                    pn.number_format = '#,##0 "zł"'
                    pn.border = _thin_border()
                    pg = ws.cell(row=r_local, column=11, value=gross)
                    pg.font = Font(name="Calibri", size=10, color=GRAY)
                    pg.alignment = Alignment(vertical="center", horizontal="right", indent=1)
                    pg.number_format = '#,##0 "zł"'
                    pg.border = _thin_border()
                    # Long names need an extra row to stay readable in 14pt+
                    # Calibri at column-A:I width.
                    ws.row_dimensions[r_local].height = 32 if len(str(name)) > 60 else 24
                    r_local += 1
            else:
                ws.merge_cells(start_row=r_local, start_column=1, end_row=r_local, end_column=11)
                empty = ws.cell(row=r_local, column=1, value=empty_text)
                empty.font = Font(name="Calibri", size=10, italic=True, color=GRAY)
                empty.alignment = Alignment(vertical="center", indent=1)
                empty.border = _thin_border()
                r_local += 1
            return r_local

        r = _write_options_block(
            opcje_row + 1,
            "Opcje fabryczne",
            factory,
            "Brak opcji fabrycznych w tej ofercie.",
        )
        r = _write_options_block(
            r,
            "Opcje dealerskie / serwisowe",
            dealer,
            "Brak opcji dealerskich / serwisowych w tej ofercie.",
        )

        footer_row = r + 1
        ws.merge_cells(start_row=footer_row, start_column=1, end_row=footer_row, end_column=11)
        f = ws.cell(row=footer_row, column=1)
        f.value = (
            "Ceny w PLN. Cena brutto liczona z VAT 23%. Oferta ważna 30 dni od daty sporządzenia. "
            "   |    Express Sp. z o.o. Sp.k."
        )
        f.font = Font(name="Calibri", size=9, italic=True, color=GRAY)
        f.alignment = Alignment(vertical="center", horizontal="center")
        ws.row_dimensions[footer_row].height = 22

        ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_options.horizontalCentered = True
        ws.page_margins = ws.page_margins.__class__(left=0.3, right=0.3, top=0.4, bottom=0.4)

    @staticmethod
    def _write_label_value(
        ws, row: int, label_col: int, value_col: int,
        label: str, value: Any, fill: str,
    ) -> None:
        la = ws.cell(row=row, column=label_col, value=label)
        la.font = Font(name="Calibri", size=10, color=GRAY)
        la.alignment = Alignment(vertical="center", indent=1)
        la.fill = PatternFill("solid", fgColor=fill)
        la.border = _thin_border()
        va = ws.cell(row=row, column=value_col, value=value)
        va.font = Font(name="Calibri", size=10, bold=True)
        va.alignment = Alignment(vertical="center", indent=1)
        va.fill = PatternFill("solid", fgColor=fill)
        va.border = _thin_border()

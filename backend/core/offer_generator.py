import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from typing import List, Dict, Any
from datetime import datetime, timedelta


class ExcelOfferGenerator:
    """
    Generates premium Excel offers using native openpyxl, mimicking the classic structure.
    """

    def __init__(self):
        # We generate everything from scratch
        self.BRAND_COLOR = "003366"  # Express "dark blue"
        self.LIGHT_BLUE = "E7F0FD"
        self.BORDER_COLOR = "D0D7DE"
        self.GRAY_TEXT = "555555"

        self.font_normal = Font(name="Calibri", size=11)
        self.font_small_gray = Font(name="Calibri", size=10, color=self.GRAY_TEXT)
        self.font_title = Font(
            name="Calibri", size=16, bold=True, color=self.BRAND_COLOR
        )
        self.font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        self.font_bold = Font(name="Calibri", size=11, bold=True)
        self.font_slogan = Font(
            name="Calibri", size=18, bold=True, color=self.BRAND_COLOR
        )

        thin = Side(border_style="thin", color="000000")
        self.border_thin = Border(top=thin, left=thin, right=thin, bottom=thin)

    def _normalize_eq(self, data: Any) -> List[str]:
        if isinstance(data, list):
            res = []
            for d in data:
                if isinstance(d, dict):
                    name = d.get("name") or d.get("description") or str(d)
                    res.append(str(name))
                elif d:
                    res.append(str(d))
            return res
        if isinstance(data, dict):
            name = data.get("name") or data.get("description")
            if name:
                return [str(name)]
            return [f"{k}: {v}" for k, v in data.items()]
        return []

    def generate_offer(
        self, client_name: str, client_nip: str, items: List[Dict[str, Any]]
    ) -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Oferta"

        # --- Column Widths ---
        widths = {
            "A": 18.0,
            "B": 40.0,
            "C": 25.0,
            "D": 25.0,
            "E": 15.0,
            "F": 12.0,
            "G": 15.0,
            "H": 12.0,
            "I": 12.0,
            "J": 12.0,
            "K": 12.0,
            "L": 25.0,
        }
        for col_letter, width in widths.items():
            ws.column_dimensions[col_letter].width = width

        # --- Document Header ---
        ws["A1"] = (
            "Express Sp. z o.o. Sp.k. | ul. Puszkarska 7F, 30-644 Kraków | www.express.pl"
        )
        ws["A1"].font = self.font_small_gray
        ws["A1"].alignment = Alignment(vertical="bottom")

        ws["H1"] = "Express | Kieruj się wygodą !"
        ws["H1"].font = self.font_slogan
        ws["H1"].alignment = Alignment(horizontal="center", vertical="center")
        ws.merge_cells("H1:L1")

        ws["A4"] = "OFERTA NAJMU DŁUGOTERMINOWEGO"
        ws["A4"].font = self.font_title
        ws["A4"].alignment = Alignment(horizontal="center", vertical="center")
        ws.merge_cells("A4:D4")

        now = datetime.now()
        valid_until = now + timedelta(days=30)

        ws["A5"] = f"Data sporządzenia oferty: {now.strftime('%Y-%m-%d')}"
        ws["A5"].font = self.font_normal
        ws["F5"] = f"Data ważności oferty: {valid_until.strftime('%Y-%m-%d')}"
        ws["F5"].font = self.font_normal

        # --- Client Info ---
        ws["A7"] = "Oferta przygotowana dla:"
        ws["A7"].font = self.font_normal
        ws["A8"] = f"{client_name}\nNIP: {client_nip}"
        ws["A8"].font = self.font_bold
        ws["A8"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells("A8:D8")

        # --- Representative Info ---
        ws["F7"] = "Oferta przygotowana przez:"
        ws["F7"].font = self.font_normal
        ws["F8"] = "Kalkulator V3 (Automated)\nSystem Ekspercki LTR\n"
        ws["F8"].font = self.font_bold
        ws["F8"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells("F8:H8")

        # --- Main Table Headers ---
        headers = [
            ("A10", "A11", "Kod\nkalkulacji"),
            ("B10", "B11", "Model\nsamochodu"),
            ("C10", "C11", "Wyposażenie\nfabryczne"),
            ("D10", "D11", "Wyposażenie\nserwisowe"),
            ("E10", "E11", "Okres\numowy"),
            ("F10", "F11", "Limit\nkm"),
            ("G10", "G11", "Czynsz\ninicjalny"),
            ("H10", "H11", "Miesięczna\ncena"),
            ("I10", "I11", "Część\nfinansowa"),
            ("J10", "J11", "Część\ntechniczna"),
            ("K10", "K11", "Opłata za\nnadprzebieg"),
            ("L10", "L11", "Rodzaj\nkosztów"),
        ]

        # Use brand blue fill for headers
        header_fill = PatternFill(
            start_color=self.BRAND_COLOR, end_color=self.BRAND_COLOR, fill_type="solid"
        )

        for top_addr, bot_addr, text in headers:
            # We construct a double row header
            col_letter = top_addr[0]
            ws[top_addr] = text.replace(
                "\n", " "
            )  # Just put it together if merging, but original split on two rows
            ws[top_addr] = text
            ws[top_addr].font = self.font_header
            ws[top_addr].alignment = Alignment(
                horizontal="center", vertical="center", wrap_text=True
            )
            ws[top_addr].fill = header_fill
            ws[top_addr].border = self.border_thin
            ws.merge_cells(f"{top_addr}:{bot_addr}")

            # Need to apply borders to merged cells properly
            ws[bot_addr].border = self.border_thin

        ws.row_dimensions[10].height = 20
        ws.row_dimensions[11].height = 20

        # --- Zebra Striping Fills ---
        fill_white = PatternFill(
            start_color="FFFFFF", end_color="FFFFFF", fill_type="solid"
        )
        fill_zebra = PatternFill(
            start_color="F2F6FA", end_color="F2F6FA", fill_type="solid"
        )

        # --- Fill Items ---
        current_row = 12
        for idx, item in enumerate(items):
            # Calculate mock splits if not provided
            net_installment = float(item.get("net_installment", 0))

            # Temporary fallback for fin/tech split if not available from backend pipeline yet
            calc_data = item.get("calculation_data") or {}
            # Assuming financial is ~70% and technical ~30% for a placeholder if not present.
            # In V3 they might be in calc_data.
            fin_part = float(calc_data.get("rata_finansowa_net", net_installment * 0.7))
            tech_part = float(
                calc_data.get("rata_serwisowa_net", net_installment * 0.3)
            )
            over_mileage = float(calc_data.get("opłata_nadprzebieg", 0.50))

            # Format equipment nicely
            factory_eq_raw = self._normalize_eq(item.get("factory_options", []))
            base_eq_raw = self._normalize_eq(item.get("standard_equipment", []))
            dealer_eq_raw = self._normalize_eq(item.get("dealer_options", []))

            # Join them, adding bullet points if missing
            def as_bullets(eq_list, max_items=10):
                formatted = []
                for e in eq_list[:max_items]:
                    e = e.strip()
                    if not e.startswith("•") and e != "":
                        formatted.append(f"• {e}")
                    elif e != "":
                        formatted.append(e)
                if len(eq_list) > max_items:
                    formatted.append(f"... i {len(eq_list) - max_items} innych")
                return "\n".join(formatted)

            factory_combined = as_bullets(base_eq_raw + factory_eq_raw)
            dealer_combined = as_bullets(dealer_eq_raw)

            toggles = calc_data.get("toggles", {})
            include_servicing = calc_data.get(
                "include_servicing", toggles.get("include_servicing", True)
            )

            if not include_servicing:
                service_type = "Brak"
            else:
                service_type = calc_data.get(
                    "service_cost_type",
                    calc_data.get("service_type", item.get("service", "ASO")),
                )
                if service_type == "nonASO":
                    service_type = "Niezależny"

            # Map the values layout
            row_vals = {
                "A": f"{datetime.now().strftime('%y%m%d')}/{idx + 1}",  # Kod kalkulacji
                "B": f"{item.get('brand', '')} {item.get('model', '')} {item.get('powertrain', '')}",
                "C": factory_combined,
                "D": dealer_combined if dealer_combined else "-",
                "E": f"{item.get('term', 0)} miesięcy",
                "F": item.get("mileage", 0),
                "G": float(item.get("contribution", 0)),
                "H": net_installment,
                "I": fin_part,
                "J": tech_part,
                "K": over_mileage,
                "L": service_type,
            }

            for col, val in row_vals.items():
                cell = ws[f"{col}{current_row}"]
                cell.value = val
                cell.font = self.font_normal
                cell.border = self.border_thin
                cell.alignment = Alignment(vertical="top", wrap_text=True)

                if col == "H":
                    cell.font = self.font_bold

                # Zebra striping
                cell.fill = fill_zebra if idx % 2 == 1 else fill_white

                # Number formatting
                if col in ["G", "H", "I", "J"]:
                    cell.number_format = '#,##0.00 "zł"'
                    cell.alignment = Alignment(horizontal="right", vertical="top")
                elif col == "F":
                    cell.number_format = "#,##0"
                    cell.alignment = Alignment(horizontal="right", vertical="top")
                elif col == "K":
                    cell.number_format = "#,##0.00"
                    cell.alignment = Alignment(horizontal="right", vertical="top")

            # Adjust row height so text fits (openpyxl does not auto-height perfectly, so we guess)
            lines = max(
                len(factory_combined.split("\n")), len(dealer_combined.split("\n")), 1
            )
            ws.row_dimensions[current_row].height = min(lines * 15 + 10, 200)

            current_row += 1

        # --- Filter & Freeze Panes ---
        ws.auto_filter.ref = f"A10:L{current_row - 1}"
        ws.freeze_panes = "A12"

        # --- Additional Information Footer ---
        footer_row = current_row + 3
        ws[f"A{footer_row}"] = "Informacje dodatkowe:"
        ws[f"A{footer_row}"].font = self.font_bold

        ws[f"A{footer_row + 1}"] = (
            "1) Wszystkie ceny podane w kalkulacji są cenami netto."
        )
        ws[f"A{footer_row + 1}"].font = self.font_normal

        ws[f"A{footer_row + 2}"] = (
            "2) Oferta ważna pod warunkiem utrzymania cen dealera."
        )
        ws[f"A{footer_row + 2}"].font = self.font_normal

        # Final bytes export
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.read()

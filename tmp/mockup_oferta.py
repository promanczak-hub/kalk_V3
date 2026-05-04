"""Mockup of the new oferta XLS layout for design review.

Generates tmp/mockup_oferta.xlsx with:
  - "Oferta" sheet: horizontal table, new columns (↗ link, ID block, prices, finansowanie)
  - one sheet per vehicle, A4 landscape, sections side-by-side
"""
from datetime import date, timedelta
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# --- Colors (matching reference offer_generator.py) ---
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


def thin(color="CCCCCC"):
    s = Side(style="thin", color=color)
    return Border(left=s, right=s, top=s, bottom=s)


def medium_navy():
    s = Side(style="medium", color=NAVY)
    return Border(left=s, right=s, top=s, bottom=s)


# --- Mock data ---
TODAY = date(2026, 5, 4)
VALID_UNTIL = TODAY + timedelta(days=30)

CLIENT = {
    "name": "SMART BUILDINGS TECHNOLOGIES SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ",
    "nip": "1234567890",
    "address": "ul. Przykładowa 1, 00-000 Warszawa",
}

PREPARED_BY = "Paweł Romańczak\nKey Account Manager\npromanczak@express.pl\n+48 600 000 000"

VEHICLES = [
    {
        "kalk_id": "0007/05/26",
        "vin": "TMBPK1NX5R3015234",
        "config_code": "5E3-NX5-2026-A1",
        "marketing_name": "SKODA OCTAVIA DRIVE SELECTION 8-bieg. DSG Liftback",
        "brand": "SKODA", "model": "Octavia IV", "trim": "Drive Selection",
        "transmission": "DSG 8-biegowa", "drive": "2x4 (przedni)",
        "fuel": "Benzyna", "engine_power_hp": 150, "body_style": "Liftback",
        "paint_metallic": True, "rv_class": "B+",
        "duration_months": 48, "annual_mileage": 180000,
        "contribution": 8000, "contribution_pct": 8.4,
        "net_installment": 2591, "financial": 1659, "technical": 932,
        "overuse_fee": 0.50, "cost_type": "ASO",
        "base_price_net": 95000,
        "factory_options_total": 13000,
        "service_options_total": 250,
        "in_rate": {
            "ubezp_oc_ac": True,
            "serwis": True, "serwis_typ": "ASO",
            "opony": True, "opony_klasa": "PREMIUM",
            "opony_rozmiar": "225/45R17", "opony_zestawy": 2,
            "ogumienie_dod_klasa": "MEDIUM",
            "auto_zastepcze": True,
            "gps": False, "oc_dodatkowe": False, "szkola_jazdy": False,
        },
        "standard": [
            "ABS", "ESP, ASR, MSR",
            "Klimatyzacja automatyczna 2-strefowa Climatronic",
            "System start-stop",
            "Czujniki parkowania przód/tył",
            "Tempomat adaptacyjny ACC",
            "Reflektory LED Matrix",
            "Apple CarPlay / Android Auto bezprzewodowe",
            "Wirtualny kokpit 10''",
            "8 poduszek powietrznych",
        ],
        "factory_options": [
            ("Pakiet Winter Plus (podgrz. fotele, kierownica)", 5000),
            ("Lakier Srebrny Smokey Diamond Metalizowany", 2500),
            ("Felgi aluminiowe 19'' Slagard Aero", 3000),
            ("Tapicerka skórzana czarna Suedia", 2500),
        ],
        "dealer_options": [
            ("Dywaniki gumowe Skoda Original", 250),
        ],
        "notes": "Klient chce odbiór w Q3. Negocjacja dodatkowego rabatu 3%.",
    },
    {
        "kalk_id": "0006/05/26",
        "vin": "TMBPK1NX5R3015199",
        "config_code": "5E3-NX5-2026-B2",
        "marketing_name": "SKODA OCTAVIA STYLE 1.5 TSI 7-bieg. DSG Liftback",
        "brand": "SKODA", "model": "Octavia IV", "trim": "Style",
        "transmission": "DSG 7-biegowa", "drive": "2x4 (przedni)",
        "fuel": "Benzyna", "engine_power_hp": 150, "body_style": "Liftback",
        "paint_metallic": True, "rv_class": "B",
        "duration_months": 48, "annual_mileage": 150000,
        "contribution": 8000, "contribution_pct": 8.4,
        "net_installment": 2433, "financial": 1613, "technical": 820,
        "overuse_fee": 0.50, "cost_type": "ASO",
        "base_price_net": 95000,
        "factory_options_total": 11500,
        "service_options_total": 250,
        "in_rate": {
            "ubezp_oc_ac": True,
            "serwis": True, "serwis_typ": "ASO",
            "opony": True, "opony_klasa": "PREMIUM",
            "opony_rozmiar": "225/45R17", "opony_zestawy": 2,
            "ogumienie_dod_klasa": "MEDIUM",
            "auto_zastepcze": True,
            "gps": False, "oc_dodatkowe": False, "szkola_jazdy": False,
        },
        "standard": [
            "ABS", "ESP", "Klimatyzacja Climatronic",
            "Czujniki parkowania", "Tempomat", "Reflektory LED",
            "Apple CarPlay / Android Auto",
        ],
        "factory_options": [
            ("Pakiet Winter Plus", 4500),
            ("Lakier metalizowany", 2500),
            ("Felgi aluminiowe 18''", 2000),
            ("Tapicerka tkanina/sztuczna skóra", 2500),
        ],
        "dealer_options": [
            ("Dywaniki gumowe", 250),
        ],
        "notes": "",
    },
    {
        "kalk_id": "0005/05/26",
        "vin": "TMBPK1NX5R3015100",
        "config_code": "5E3-NX5-2026-C3",
        "marketing_name": "SKODA OCTAVIA AMBITION 1.5 TSI MT 6-bieg. Liftback",
        "brand": "SKODA", "model": "Octavia IV", "trim": "Ambition",
        "transmission": "MT 6-biegowa", "drive": "2x4 (przedni)",
        "fuel": "Benzyna", "engine_power_hp": 150, "body_style": "Liftback",
        "paint_metallic": False, "rv_class": "B-",
        "duration_months": 48, "annual_mileage": 120000,
        "contribution": 8000, "contribution_pct": 8.4,
        "net_installment": 2310, "financial": 1567, "technical": 743,
        "overuse_fee": 0.50, "cost_type": "ASO",
        "base_price_net": 92000,
        "factory_options_total": 8500,
        "service_options_total": 0,
        "in_rate": {
            "ubezp_oc_ac": True,
            "serwis": True, "serwis_typ": "ASO",
            "opony": True, "opony_klasa": "MEDIUM",
            "opony_rozmiar": "205/55R16", "opony_zestawy": 2,
            "ogumienie_dod_klasa": "BUDGET",
            "auto_zastepcze": False,
            "gps": False, "oc_dodatkowe": False, "szkola_jazdy": False,
        },
        "standard": [
            "ABS", "ESP", "Klimatyzacja manualna",
            "Czujniki parkowania tył", "Tempomat",
            "Apple CarPlay / Android Auto",
        ],
        "factory_options": [
            ("Pakiet Comfort", 3000),
            ("Felgi aluminiowe 17''", 1500),
            ("Tapicerka tkanina premium", 2000),
            ("System multimedialny powiększony", 2000),
        ],
        "dealer_options": [],
        "notes": "Wariant podstawowy do rozważenia.",
    },
]


def safe_sheet_name(kalk_id: str) -> str:
    """Excel sheet name: max 31 chars, no : \\ / ? * [ ]"""
    cleaned = kalk_id.replace("/", "-").replace("\\", "-")[:31]
    return cleaned


def write_oferta_sheet(wb: Workbook, vehicles: list[dict]):
    ws = wb.create_sheet("Oferta", 0)

    # === HEADER BAND (rows 1-8) ===
    # Row 1: company info (left), slogan (right)
    ws.merge_cells("A1:F1")
    ws["A1"] = "Express Sp. z o.o. Sp.k. | ul. Puszkarska 7F, 30-644 Kraków | www.express.pl"
    ws["A1"].font = Font(name="Calibri", size=10, color=GRAY)
    ws["A1"].alignment = Alignment(vertical="center", horizontal="left")

    ws.merge_cells("J1:N1")
    ws["J1"] = "Express | Kieruj się wygodą !"
    ws["J1"].font = Font(name="Calibri", size=18, bold=True, color=NAVY)
    ws["J1"].alignment = Alignment(vertical="center", horizontal="right")
    ws.row_dimensions[1].height = 65

    # Row 2-3: visual gap
    ws.row_dimensions[2].height = 0.75
    ws.row_dimensions[3].height = 0.75

    # Row 4: title
    ws.merge_cells("A4:N4")
    ws["A4"] = "OFERTA NAJMU DŁUGOTERMINOWEGO"
    ws["A4"].font = Font(name="Calibri", size=16, bold=True, color=NAVY)
    ws["A4"].alignment = Alignment(vertical="center", horizontal="center")
    ws.row_dimensions[4].height = 30

    # Row 5: dates
    ws.merge_cells("A5:E5")
    ws["A5"] = f"Data sporządzenia oferty: {TODAY:%Y-%m-%d}"
    ws["A5"].font = Font(name="Calibri", size=10, color=DARK_GRAY)
    ws.merge_cells("F5:N5")
    ws["F5"] = f"Data ważności oferty: {VALID_UNTIL:%Y-%m-%d}"
    ws["F5"].font = Font(name="Calibri", size=11, color=DARK_GRAY)
    ws["F5"].alignment = Alignment(horizontal="right")

    ws.row_dimensions[6].height = 5

    # Row 7-8: client / prepared by
    ws.merge_cells("A7:F8")
    ws["A7"] = f"Oferta przygotowana dla:\n{CLIENT['name']}\nNIP: {CLIENT['nip']}\n{CLIENT['address']}"
    ws["A7"].font = Font(name="Calibri", size=10, bold=True, color=NAVY)
    ws["A7"].fill = PatternFill("solid", fgColor=SOFT_BLUE)
    ws["A7"].alignment = Alignment(vertical="center", wrap_text=True, indent=1)

    ws.merge_cells("G7:N8")
    ws["G7"] = f"Oferta przygotowana przez:\n{PREPARED_BY}"
    ws["G7"].font = Font(name="Calibri", size=10, bold=True, color=NAVY)
    ws["G7"].fill = PatternFill("solid", fgColor=SOFT_BLUE)
    ws["G7"].alignment = Alignment(vertical="center", wrap_text=True, indent=1)
    ws.row_dimensions[7].height = 32
    ws.row_dimensions[8].height = 32

    ws.row_dimensions[9].height = 10

    # === TABLE HEADERS (row 10) ===
    headers = [
        ("A", "↗", 4),
        ("B", "Numer oferty\nVIN\nKonfiguracja", 22),
        ("C", "Model", 38),
        ("D", "Cena katalogowa\nnetto", 14),
        ("E", "Cena opcji\nfabrycznych", 13),
        ("F", "Cena opcji\nserwisowych", 13),
        ("G", "Okres\numowy", 9),
        ("H", "Limit\nkm", 10),
        ("I", "Czynsz\ninicjalny", 11),
        ("J", "Miesięczna\ncena netto", 13),
        ("K", "Część\nfinansowa", 11),
        ("L", "Część\ntechniczna", 11),
        ("M", "Opłata za\nnadprzebieg", 12),
        ("N", "Rodzaj\nkosztów", 11),
    ]
    for col, label, width in headers:
        ws.column_dimensions[col].width = width
        c = ws[f"{col}10"]
        c.value = label
        c.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
        c.border = thin(NAVY)
    ws.row_dimensions[10].height = 40

    # === DATA ROWS ===
    for i, v in enumerate(vehicles):
        row = 11 + i
        sheet_name = safe_sheet_name(v["kalk_id"])
        zebra = ZEBRA if i % 2 == 1 else WHITE

        # A: hyperlink icon
        a = ws.cell(row=row, column=1)
        a.value = "↗"
        a.hyperlink = f"#'{sheet_name}'!A1"
        a.font = Font(name="Calibri", size=14, bold=True, color=LINK_BLUE, underline="single")
        a.alignment = Alignment(vertical="center", horizontal="center")
        a.fill = PatternFill("solid", fgColor=zebra)

        # B: ID block (multi-line)
        b = ws.cell(row=row, column=2)
        b.value = f"{v['kalk_id']}\nVIN: {v['vin']}\nKonf: {v['config_code']}"
        b.font = Font(name="Calibri", size=9, color=DARK_GRAY)
        b.alignment = Alignment(vertical="center", wrap_text=True, indent=1)
        b.fill = PatternFill("solid", fgColor=zebra)

        # C: marketing name
        c = ws.cell(row=row, column=3)
        c.value = v["marketing_name"]
        c.font = Font(name="Calibri", size=11, bold=True)
        c.alignment = Alignment(vertical="center", wrap_text=True, indent=1)
        c.fill = PatternFill("solid", fgColor=zebra)

        # D-F: prices
        ws.cell(row=row, column=4, value=v["base_price_net"])
        ws.cell(row=row, column=5, value=v["factory_options_total"])
        ws.cell(row=row, column=6, value=v["service_options_total"])

        # G-N: contract & finance
        ws.cell(row=row, column=7, value=f"{v['duration_months']} miesięcy")
        ws.cell(row=row, column=8, value=v["annual_mileage"])
        ws.cell(row=row, column=9, value=v["contribution"])
        rata = ws.cell(row=row, column=10, value=v["net_installment"])
        ws.cell(row=row, column=11, value=v["financial"])
        ws.cell(row=row, column=12, value=v["technical"])
        ws.cell(row=row, column=13, value=v["overuse_fee"])
        ws.cell(row=row, column=14, value=v["cost_type"])

        # Style numeric cells
        for col_idx in range(4, 15):
            cell = ws.cell(row=row, column=col_idx)
            cell.font = Font(name="Calibri", size=11)
            cell.alignment = Alignment(vertical="center", horizontal="center")
            cell.fill = PatternFill("solid", fgColor=zebra)
            if col_idx in (4, 5, 6, 9, 10, 11, 12):
                cell.number_format = '#,##0 "zł"'
            elif col_idx == 8:
                cell.number_format = "#,##0"
            elif col_idx == 13:
                cell.number_format = '0.00 "zł/km"'

        # Highlight rata column
        rata.font = Font(name="Calibri", size=12, bold=True, color=NAVY)
        rata.fill = PatternFill("solid", fgColor=YELLOW)

        # All cells: thin border
        for col_idx in range(1, 15):
            ws.cell(row=row, column=col_idx).border = thin()

        ws.row_dimensions[row].height = 50

    # === FOOTER ===
    last_row = 11 + len(vehicles) + 1
    ws.cell(row=last_row, column=1, value="Informacje dodatkowe:").font = Font(
        name="Calibri", size=10, bold=True, color=GRAY
    )
    ws.merge_cells(start_row=last_row + 1, start_column=1, end_row=last_row + 1, end_column=14)
    foot = ws.cell(row=last_row + 1, column=1)
    foot.value = (
        "1) Wszystkie ceny podane w kalkulacji są cenami netto.\n"
        "2) Oferta ważna pod warunkiem akceptacji klienta przed datą wygaśnięcia.\n"
        "3) Kliknij ikonę ↗ przy danym pojeździe, aby zobaczyć pełną specyfikację."
    )
    foot.font = Font(name="Calibri", size=9, color=GRAY)
    foot.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[last_row + 1].height = 50

    # Print setup
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_options.horizontalCentered = True
    ws.page_margins = ws.page_margins.__class__(left=0.3, right=0.3, top=0.4, bottom=0.4)


def write_vehicle_sheet(wb: Workbook, v: dict):
    sheet_name = safe_sheet_name(v["kalk_id"])
    ws = wb.create_sheet(sheet_name)

    # Column widths — 12 columns total, 4 sections of 3 cols each
    widths = {
        "A": 18, "B": 18, "C": 4,
        "D": 16, "E": 14, "F": 4,
        "G": 16, "H": 14, "I": 4,
        "J": 16, "K": 22, "L": 4,
    }
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    # === ROW 1: top bar — back link + branding + kalk_id ===
    back = ws["A1"]
    back.value = "← Wróć do oferty"
    back.hyperlink = "#Oferta!A1"
    back.font = Font(name="Calibri", size=11, bold=True, color=LINK_BLUE, underline="single")
    back.alignment = Alignment(vertical="center", indent=1)

    ws.merge_cells("D1:H1")
    ws["D1"] = "Express | Kieruj się wygodą !"
    ws["D1"].font = Font(name="Calibri", size=14, bold=True, color=NAVY)
    ws["D1"].alignment = Alignment(vertical="center", horizontal="center")

    ws.merge_cells("J1:K1")
    ws["J1"] = f"Kalkulacja: {v['kalk_id']}"
    ws["J1"].font = Font(name="Calibri", size=10, color=GRAY)
    ws["J1"].alignment = Alignment(vertical="center", horizontal="right")
    ws.row_dimensions[1].height = 30

    # Row 2: spacer
    ws.row_dimensions[2].height = 5

    # === ROW 3-4: HERO ===
    ws.merge_cells("A3:K3")
    ws["A3"] = v["marketing_name"]
    ws["A3"].font = Font(name="Calibri", size=18, bold=True, color=NAVY)
    ws["A3"].alignment = Alignment(vertical="center", horizontal="center")
    ws.row_dimensions[3].height = 32

    ws.merge_cells("A4:K4")
    ws["A4"] = f"Rata miesięczna netto: {v['net_installment']:,} zł".replace(",", " ")
    ws["A4"].font = Font(name="Calibri", size=14, bold=True, color=NAVY)
    ws["A4"].alignment = Alignment(vertical="center", horizontal="center")
    ws["A4"].fill = PatternFill("solid", fgColor=YELLOW)
    ws.row_dimensions[4].height = 28

    # Row 5: spacer
    ws.row_dimensions[5].height = 8

    # === ROW 6: section headers ===
    headers = [
        ("A6:B6", "POJAZD"),
        ("D6:E6", "WARUNKI FINANSOWANIA"),
        ("G6:H6", "W CENIE RATY"),
        ("J6:K6", "WYPOSAŻENIE STANDARDOWE"),
    ]
    for rng, label in headers:
        ws.merge_cells(rng)
        c = ws[rng.split(":")[0]]
        c.value = label
        c.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(vertical="center", horizontal="center")
    ws.row_dimensions[6].height = 22

    # === Section content (rows 7+) ===
    pojazd_rows = [
        ("Marka", v["brand"]),
        ("Model", v["model"]),
        ("Wersja", v["trim"]),
        ("Silnik", f"{v['engine_power_hp']} KM"),
        ("Paliwo", v["fuel"]),
        ("Skrzynia", v["transmission"]),
        ("Napęd", v["drive"]),
        ("Typ nadwozia", v["body_style"]),
        ("Lakier metalik", "Tak" if v["paint_metallic"] else "Nie"),
        ("Klasa RV", v["rv_class"]),
    ]

    warunki_rows = [
        ("Okres umowy", f"{v['duration_months']} miesięcy"),
        ("Limit km/rok", f"{v['annual_mileage']:,}".replace(",", " ")),
        ("Czynsz inicjalny", f"{v['contribution']:,} zł ({v['contribution_pct']}%)".replace(",", " ")),
        ("Rata miesięczna netto", f"{v['net_installment']:,} zł".replace(",", " ")),
        ("Część finansowa", f"{v['financial']:,} zł".replace(",", " ")),
        ("Część techniczna", f"{v['technical']:,} zł".replace(",", " ")),
        ("Opłata za nadprzebieg", f"{v['overuse_fee']:.2f} zł/km"),
        ("Rodzaj kosztów", v["cost_type"]),
    ]

    ir = v["in_rate"]
    in_rate_rows = [
        ("Ubezpieczenie OC/AC", ir["ubezp_oc_ac"]),
        ("Serwis", f"{ir['serwis_typ']}" if ir["serwis"] else False),
        ("Opony", f"{ir['opony_klasa']} • {ir['opony_rozmiar']}" if ir["opony"] else False),
        ("Liczba zestawów opon", f"{ir['opony_zestawy']}" if ir["opony"] else False),
        ("Klasa ogumienia dodatk.", ir["ogumienie_dod_klasa"] if ir["opony"] else False),
        ("Auto zastępcze", ir["auto_zastepcze"]),
        ("GPS", ir["gps"]),
        ("OC dodatkowe", ir["oc_dodatkowe"]),
        ("Szkoła jazdy", ir["szkola_jazdy"]),
    ]

    standard_rows = [(item, "") for item in v["standard"]]

    max_section_rows = max(len(pojazd_rows), len(warunki_rows), len(in_rate_rows), len(standard_rows))

    for i in range(max_section_rows):
        r = 7 + i
        zebra = ZEBRA if i % 2 == 0 else WHITE

        # POJAZD: A label, B value
        if i < len(pojazd_rows):
            label, val = pojazd_rows[i]
            la = ws.cell(row=r, column=1, value=label)
            la.font = Font(name="Calibri", size=10, color=GRAY)
            la.alignment = Alignment(vertical="center", indent=1)
            la.fill = PatternFill("solid", fgColor=zebra)
            la.border = thin()
            va = ws.cell(row=r, column=2, value=val)
            va.font = Font(name="Calibri", size=10, bold=True)
            va.alignment = Alignment(vertical="center", indent=1)
            va.fill = PatternFill("solid", fgColor=zebra)
            va.border = thin()

        # WARUNKI: D label, E value
        if i < len(warunki_rows):
            label, val = warunki_rows[i]
            la = ws.cell(row=r, column=4, value=label)
            la.font = Font(name="Calibri", size=10, color=GRAY)
            la.alignment = Alignment(vertical="center", indent=1)
            la.fill = PatternFill("solid", fgColor=zebra)
            la.border = thin()
            va = ws.cell(row=r, column=5, value=val)
            highlight = label == "Rata miesięczna netto"
            va.font = Font(
                name="Calibri", size=11 if highlight else 10,
                bold=True, color=NAVY if highlight else "000000"
            )
            va.alignment = Alignment(vertical="center", horizontal="right", indent=1)
            va.fill = PatternFill("solid", fgColor=YELLOW if highlight else zebra)
            va.border = thin()

        # W CENIE RATY: G label, H value (✓/✗ + extra info)
        if i < len(in_rate_rows):
            label, val = in_rate_rows[i]
            la = ws.cell(row=r, column=7, value=label)
            la.font = Font(name="Calibri", size=10, color=GRAY)
            la.alignment = Alignment(vertical="center", indent=1)
            la.fill = PatternFill("solid", fgColor=zebra)
            la.border = thin()
            va = ws.cell(row=r, column=8)
            if val is True or (isinstance(val, str) and val):
                va.value = f"✓ {val}" if isinstance(val, str) else "✓"
                va.font = Font(name="Calibri", size=10, bold=True, color=GREEN_OK)
            else:
                va.value = "✗"
                va.font = Font(name="Calibri", size=10, bold=True, color=RED_NO)
            va.alignment = Alignment(vertical="center", indent=1)
            va.fill = PatternFill("solid", fgColor=zebra)
            va.border = thin()

        # STANDARD: J:K merged bullet item
        if i < len(standard_rows):
            ws.merge_cells(start_row=r, start_column=10, end_row=r, end_column=11)
            la = ws.cell(row=r, column=10, value=f"•  {standard_rows[i][0]}")
            la.font = Font(name="Calibri", size=10)
            la.alignment = Alignment(vertical="center", wrap_text=True, indent=1)
            la.fill = PatternFill("solid", fgColor=zebra)
            la.border = thin()

        ws.row_dimensions[r].height = 20

    # === Bottom sections: NOTATKI (left) + OPCJE FABR/DEALER (right) ===
    bottom_start = 7 + max_section_rows + 1
    ws.row_dimensions[bottom_start - 1].height = 8

    # Section headers
    ws.merge_cells(start_row=bottom_start, start_column=1, end_row=bottom_start, end_column=5)
    nh = ws.cell(row=bottom_start, column=1, value="NOTATKI")
    nh.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
    nh.fill = PatternFill("solid", fgColor=NAVY)
    nh.alignment = Alignment(vertical="center", horizontal="center")

    ws.merge_cells(start_row=bottom_start, start_column=7, end_row=bottom_start, end_column=11)
    oh = ws.cell(row=bottom_start, column=7, value="OPCJE — CENY NETTO")
    oh.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
    oh.fill = PatternFill("solid", fgColor=NAVY)
    oh.alignment = Alignment(vertical="center", horizontal="center")
    ws.row_dimensions[bottom_start].height = 22

    # Notatki body
    notes_rows_count = max(4, len(v["factory_options"]) + len(v["dealer_options"]) + 3)
    ws.merge_cells(
        start_row=bottom_start + 1, start_column=1,
        end_row=bottom_start + notes_rows_count, end_column=5
    )
    nb = ws.cell(row=bottom_start + 1, column=1, value=v["notes"] or "—")
    nb.font = Font(name="Calibri", size=10, color=DARK_GRAY)
    nb.alignment = Alignment(vertical="top", wrap_text=True, indent=1)
    nb.fill = PatternFill("solid", fgColor=ZEBRA)
    nb.border = thin()

    # Opcje fabryczne header
    r = bottom_start + 1
    ws.merge_cells(start_row=r, start_column=7, end_row=r, end_column=10)
    ws.cell(row=r, column=7, value="Opcje fabryczne").font = Font(name="Calibri", size=10, bold=True, color=NAVY)
    ws.cell(row=r, column=7).alignment = Alignment(vertical="center", indent=1)
    ws.cell(row=r, column=11, value="cena netto").font = Font(name="Calibri", size=10, bold=True, color=NAVY)
    ws.cell(row=r, column=11).alignment = Alignment(vertical="center", horizontal="right", indent=1)
    r += 1

    for name, price in v["factory_options"]:
        ws.merge_cells(start_row=r, start_column=7, end_row=r, end_column=10)
        nm = ws.cell(row=r, column=7, value=name)
        nm.font = Font(name="Calibri", size=10)
        nm.alignment = Alignment(vertical="center", indent=1)
        nm.border = thin()
        pr = ws.cell(row=r, column=11, value=price)
        pr.font = Font(name="Calibri", size=10)
        pr.alignment = Alignment(vertical="center", horizontal="right", indent=1)
        pr.number_format = '#,##0 "zł"'
        pr.border = thin()
        r += 1

    # Separator + Opcje dealerskie
    if v["dealer_options"]:
        ws.merge_cells(start_row=r, start_column=7, end_row=r, end_column=11)
        sep = ws.cell(row=r, column=7, value="Opcje dealerskie / serwisowe")
        sep.font = Font(name="Calibri", size=10, bold=True, color=NAVY)
        sep.alignment = Alignment(vertical="center", indent=1)
        sep.fill = PatternFill("solid", fgColor=SOFT_BLUE)
        r += 1

        for name, price in v["dealer_options"]:
            ws.merge_cells(start_row=r, start_column=7, end_row=r, end_column=10)
            nm = ws.cell(row=r, column=7, value=name)
            nm.font = Font(name="Calibri", size=10)
            nm.alignment = Alignment(vertical="center", indent=1)
            nm.border = thin()
            pr = ws.cell(row=r, column=11, value=price)
            pr.font = Font(name="Calibri", size=10)
            pr.alignment = Alignment(vertical="center", horizontal="right", indent=1)
            pr.number_format = '#,##0 "zł"'
            pr.border = thin()
            r += 1

    # === FOOTER ===
    footer_row = max(r + 2, bottom_start + notes_rows_count + 2)
    ws.merge_cells(start_row=footer_row, start_column=1, end_row=footer_row, end_column=11)
    f = ws.cell(row=footer_row, column=1)
    f.value = "Ceny netto. Oferta ważna 30 dni od daty sporządzenia.    |    Express Sp. z o.o. Sp.k."
    f.font = Font(name="Calibri", size=9, italic=True, color=GRAY)
    f.alignment = Alignment(vertical="center", horizontal="center")
    ws.row_dimensions[footer_row].height = 22

    # Print setup: A4 landscape
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_options.horizontalCentered = True
    ws.page_margins = ws.page_margins.__class__(left=0.3, right=0.3, top=0.4, bottom=0.4)


def main():
    wb = Workbook()
    wb.remove(wb.active)

    write_oferta_sheet(wb, VEHICLES)
    for v in VEHICLES:
        write_vehicle_sheet(wb, v)

    out = Path(__file__).parent / "mockup_oferta.xlsx"
    wb.save(out)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()

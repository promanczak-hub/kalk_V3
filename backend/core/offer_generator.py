import io
import os
import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from typing import List, Dict, Any

class ExcelOfferGenerator:
    def __init__(self, template_path: str = "templates/template_oferta.xlsx"):
        # Make sure path is relative to current working dir or absolute
        self.template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), template_path)
    
    def generate_offer(self, client_name: str, client_nip: str, items: List[Dict[str, Any]]) -> bytes:
        """
        Generates an Excel offer byte stream from a list of offer items.
        """
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"Template not found at {self.template_path}")

        wb = openpyxl.load_workbook(self.template_path)
        
        # 1. Fill the "Zestawienie" (Summary) sheet
        ws_summary = wb["Zestawienie"]
        
        # Fill client data
        ws_summary["B2"] = client_name
        ws_summary["B3"] = client_nip
        
        start_row = 6
        cheapest_idx = -1
        lowest_installment = float('inf')
        
        # Find the cheapest installment to highlight later
        for idx, item in enumerate(items):
            net_inst = float(item.get("net_installment", 0))
            if net_inst < lowest_installment and net_inst > 0:
                lowest_installment = net_inst
                cheapest_idx = idx

        for idx, item in enumerate(items):
            current_row = start_row + idx
            
            ws_summary.cell(row=current_row, column=1, value=item.get("brand", ""))
            ws_summary.cell(row=current_row, column=2, value=item.get("model", ""))
            ws_summary.cell(row=current_row, column=3, value=item.get("powertrain", ""))
            ws_summary.cell(row=current_row, column=4, value=item.get("vin_or_config", ""))
            ws_summary.cell(row=current_row, column=5, value=item.get("term", 0))
            ws_summary.cell(row=current_row, column=6, value=item.get("mileage", 0))
            
            # Formatting as currency if needed, just rounding here
            inst_value = round(float(item.get("net_installment", 0)), 2)
            ws_summary.cell(row=current_row, column=7, value=inst_value)
            
            # Recommendation
            recommendation = item.get("system_recommendation", "")
            if idx == cheapest_idx:
                recommendation = "Najniższa Rata" if not recommendation else f"{recommendation} + Najniższa Rata"
                # Highlight row in light green
                green_fill = PatternFill("solid", fgColor="E2EFDA")
                for col in range(1, 9):
                    ws_summary.cell(row=current_row, column=col).fill = green_fill
            
            ws_summary.cell(row=current_row, column=8, value=recommendation)

        # 2. Add dynamic sheets for each vehicle's specification
        for item in items:
            vin = item.get("vin_or_config", "Auto")
            safe_title = str(vin)[:31] # max length for sheet title
            
            # Create a new sheet
            ws = wb.create_sheet(title=safe_title)
            
            # Title
            ws["A1"] = f"Specyfikacja Pojazdu: {item.get('brand', '')} {item.get('model', '')}"
            ws["A1"].font = Font(size=16, bold=True)
            ws["A2"] = f"Identyfikator: {vin}"
            
            current_row = 4
            
            # Standard Equipment
            standard_eq = item.get("standard_equipment", [])
            ws.cell(row=current_row, column=1, value="Wyposażenie Standardowe").font = Font(bold=True)
            current_row += 1
            if not standard_eq:
                ws.cell(row=current_row, column=1, value="Brak danych")
                current_row += 1
            else:
                for eq in standard_eq:
                    ws.cell(row=current_row, column=1, value=f"• {eq}")
                    current_row += 1
            
            current_row += 1
            
            # Factory Options
            factory_opt = item.get("factory_options", [])
            ws.cell(row=current_row, column=1, value="Opcje Fabryczne (Płatne)").font = Font(bold=True)
            current_row += 1
            if not factory_opt:
                ws.cell(row=current_row, column=1, value="Brak danych")
                current_row += 1
            else:
                for eq in factory_opt:
                    ws.cell(row=current_row, column=1, value=f"• {eq}")
                    current_row += 1
                    
            current_row += 1
            
            # Dealer Options (Serwisowe itp.)
            dealer_opt = item.get("dealer_options", [])
            ws.cell(row=current_row, column=1, value="Opcje Dealerskie / Dodatkowe").font = Font(bold=True)
            current_row += 1
            if not dealer_opt:
                ws.cell(row=current_row, column=1, value="Brak danych")
                current_row += 1
            else:
                for eq in dealer_opt:
                    ws.cell(row=current_row, column=1, value=f"• {eq}")
                    current_row += 1
            
            ws.column_dimensions["A"].width = 80

        # Output to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.read()

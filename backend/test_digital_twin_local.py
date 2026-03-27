import sys
import os
import json

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../d/kalk_v3/backend"))
)

from core.pipeline_digital_twin import extract_digital_twin_from_pdf

with open("D:\\kalk_v3\\backend\\passat_test.pdf", "rb") as f:
    pdf_bytes = f.read()

print("Rozpoczynam ekstrakcję Passata przez Pydantic Structured Outputs...")
result = extract_digital_twin_from_pdf(pdf_bytes, mime_type="application/pdf")

print("Zwrócony Unified Data:")
print(json.dumps(result, indent=2, ensure_ascii=False))

"""Verify SAMAR mapper now works with samar_classes table."""

import os

os.environ.setdefault("VITE_SUPABASE_URL", "http://127.0.0.1:54321")
os.environ.setdefault(
    "VITE_SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9."
    "CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0",
)
os.environ.setdefault("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

from core.samar_mapper import map_to_samar_class

# Test: CUPRA TERRAMAR SUV
code, name, candidates = map_to_samar_class(
    brand="CUPRA",
    model="TERRAMAR",
    body_style="SUV",
    segment=None,
    trim="1.5 e-TSI 150 KM 7-biegowa automatyczna - DSG",
    transmission="Automatyczna (DSG)",
    number_of_seats=None,
)

print(f"Result: code={code}, name={name}")
print(f"Top 5 candidates:")
for c in candidates[:5]:
    print(f"  {c['klasa']:50} confidence={c['confidence']}")

if name == "INNE - WYMAGA RĘCZNEGO MAPOWANIA":
    print("\n❌ STILL BROKEN - fallback returned!")
else:
    print(f"\n✅ SUCCESS - mapped to: {name}")

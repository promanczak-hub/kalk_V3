"""Quick test: simulate the full samar_class resolution chain."""

from core import samar_rv

samar_rv._SAMAR_CACHE = {}  # clear

from core.samar_rv import get_samar_class_id

# Test both formats
old_name = "PODSTAWOWA D SREDNIA"  # ASCII approximation
result_old = get_samar_class_id("PODSTAWOWA D ŚREDNIA")
result_new = get_samar_class_id("PODSTAWOWA Klasa D ŚREDNIA")

with open("tmp_resolve_out.txt", "w", encoding="utf-8") as f:
    f.write(f"OLD format → {result_old}\n")
    f.write(f"NEW format → {result_new}\n")
    f.write(f"Cache entries: {len(samar_rv._SAMAR_CACHE)}\n")
    for k, v in sorted(samar_rv._SAMAR_CACHE.items()):
        f.write(f"  '{k}' → {v}\n")

print("Done - see tmp_resolve_out.txt")

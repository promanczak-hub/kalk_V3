
with open("d:/kalk_v3/backend/core/samar_rv.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

def find_line(lines, substr):
    for i, l in enumerate(lines):
        if substr in l:
            return i
    return -1

class_start = find_line(lines, "class SamarRVCalculator:")
class_end = find_line(lines, "@lru_cache(maxsize=128)\ndef fetch_color_correction_cached")
if class_end == -1:
    class_end = find_line(lines, "def fetch_color_correction_cached(") - 1

monkey_start = find_line(lines, "def _sc_fetch_color_correction(self) -> float:")
sc_block_end = find_line(lines, "SamarRVCalculator._fetch_color_correction = _sc_fetch_color_correction")

new_lines = []
# 0 to class_end
new_lines.extend(lines[:class_end])

# insert indented methods
for line in lines[monkey_start:sc_block_end]:
    # if it's the monkey patch header, ignore
    if "Monkey-patching" in line or "══" in line:
        continue
    if line.strip() == "":
        new_lines.append(line)
    elif line.startswith("def _sc_"):
        new_lines.append("    def " + line[8:])
    elif not line.startswith("    ") and not line.startswith("#") and line.strip() != "":
        new_lines.append("    " + line)
    else:
        new_lines.append("    " + line)

# add the globals
new_lines.extend(lines[class_end:monkey_start])

# remove monkey patching block from the end
sc_block_start_header = find_line(lines, "Monkey-patching:")
# write back
with open("d:/kalk_v3/backend/core/samar_rv.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

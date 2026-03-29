import json
with open("d:/kalk_v3/backend/calc_ab33_2.py", "r") as f:
    text = f.read()

# I will execute calc_ab33_2.py but inject the trace printing
import sys
import io

try:
    exec(text)
except Exception as e:
    print(e)

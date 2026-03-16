import sys
import os
sys.path.append(os.path.abspath('d:/kalk_v3/backend'))
from core.LTRKalkulator import _resolve_engine_type_id
print(_resolve_engine_type_id('SILNIK: Diesel (ON)'))

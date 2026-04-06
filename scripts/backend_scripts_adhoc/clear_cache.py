import os
import sys

from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.redis_cache import cache_invalidate_pattern

n_initial = cache_invalidate_pattern("initial_data")
n_filters = cache_invalidate_pattern("filters:*")
print(f"Cleared {n_initial} initial_data keys and {n_filters} filters keys.")

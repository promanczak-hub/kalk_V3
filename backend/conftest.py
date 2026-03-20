"""Root conftest — adds backend root to sys.path so tests can import core/api."""

import sys
from pathlib import Path

# Allow "import core" and "import api" from anywhere pytest is run
sys.path.insert(0, str(Path(__file__).parent))

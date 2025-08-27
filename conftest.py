import sys
from pathlib import Path

# Ensure project root (containing 'app') is on sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sys
from pathlib import Path

# Make the ``conduct`` package importable without requiring the caller to set
# PYTHONPATH. The parent skills directory goes on sys.path so tests import
# ``conduct.<module>`` rather than relying on flat top-level module names.
_SKILLS_DIR = Path(__file__).resolve().parents[2]
if str(_SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILLS_DIR))

import sys
from pathlib import Path

# Make the skill package importable under its own directory without requiring
# the caller to set PYTHONPATH. Tests import ``parser``, ``marker``, ``lock``
# as top-level modules.
_SKILL_DIR = Path(__file__).resolve().parent.parent
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

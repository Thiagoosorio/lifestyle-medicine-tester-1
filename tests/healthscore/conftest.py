"""Path setup for the healthscore Phase 0 test tree.

Adds ``<repo>/src`` to sys.path so ``import healthscore`` resolves
without needing to modify the existing repo's pyproject.toml.

Scoped to this directory only -- the existing tests/conftest.py at the
repo root is unaffected.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_PATH = _REPO_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

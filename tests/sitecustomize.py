"""Make direct test-file runs resolve project packages.

When a test is started from inside ``tests`` or as ``python tests/test_*.py``,
Python may put only the tests directory on ``sys.path``.  Add the repository
root so imports such as ``backend.backend_api`` work in those runners too.
"""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
ROOT_PATH = str(ROOT)

if ROOT_PATH not in sys.path:
    sys.path.insert(0, ROOT_PATH)

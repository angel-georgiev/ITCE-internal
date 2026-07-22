import sys
from pathlib import Path

import pytest

# Make the repo root importable so `import tracker` works under pytest.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def html_fixture():
    def _load(name: str) -> str:
        return (FIXTURES / "html" / name).read_text(encoding="utf-8")

    return _load

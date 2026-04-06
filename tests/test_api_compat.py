"""API compatibility tests.

Verifies that the current .pyi stubs are backward-compatible with the
baseline snapshot in tests/fixtures/.  Any MISSING or CHANGED symbols
cause the test to fail.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

from verify_api import extract_api, compare_apis


BASELINE_IMGUI = ROOT / "tests" / "fixtures" / "imgui_baseline.pyi"
CURRENT_IMGUI = ROOT / "src" / "slimgui" / "slimgui_ext" / "imgui.pyi"


@pytest.mark.skipif(not CURRENT_IMGUI.exists(), reason="stubs not generated yet")
def test_imgui_api_no_missing():
    """No symbols from the baseline may be removed."""
    baseline = extract_api(str(BASELINE_IMGUI))
    current = extract_api(str(CURRENT_IMGUI))
    missing, _changed, _added = compare_apis(baseline, current)
    assert not missing, "API symbols removed:\n" + "\n".join(missing)


@pytest.mark.skipif(not CURRENT_IMGUI.exists(), reason="stubs not generated yet")
def test_imgui_api_no_signature_changes():
    """No function/method signatures may change."""
    baseline = extract_api(str(BASELINE_IMGUI))
    current = extract_api(str(CURRENT_IMGUI))
    _missing, changed, _added = compare_apis(baseline, current)
    assert not changed, "API signatures changed:\n" + "\n".join(changed)

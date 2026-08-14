"""
Epic 3.3: README / PRODUCT / AGENTS stay aligned with this repo root.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent

DOC_FILES = ("README.md", "PRODUCT.md", "AGENTS.md", "NEXT_STEPS.md", "MINI_DECOMP.md")


def test_docs_do_not_point_at_stale_artifacts_path():
    for name in DOC_FILES:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "cd artifacts/algorithm-oracle" not in text, f"{name} still uses artifacts/ path"


def test_readme_quickstart_and_status_are_current():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "pip install -r requirements.txt" in text
    assert "streamlit run app/streamlit_app.py" in text
    assert "run_checks.sh" in text
    assert "run_checks.ps1" in text
    assert "outside_verifiable_range" in text
    assert "pseudocode first" in text.lower()


def test_product_v1_teeth_are_checked():
    text = (ROOT / "PRODUCT.md").read_text(encoding="utf-8")
    assert "- [x] `run_checks.sh`" in text
    assert "- [x] Classifier regression" in text
    assert "- [x] When verification is not applicable" in text
    assert "- [ ]" not in text.split("## Success criteria")[1].split("## Sample demos")[0]


def test_agents_lists_both_gatekeepers():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "./run_checks.sh" in text
    assert ".\\run_checks.ps1" in text

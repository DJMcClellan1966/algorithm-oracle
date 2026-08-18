"""
Epic 3.1: Streamlit view is pseudocode-first with an explicit Python toggle.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from app.ui import (
    DEFAULT_SHOW_PYTHON,
    EXAMPLES,
    can_toggle_python,
    source_path_label,
    toggle_label,
    visible_code,
)

PSEUDO = "sort by finish time\nselect earliest"
PYTHON = "def solve(activities):\n    return []"


def test_default_view_is_pseudocode_not_python():
    assert DEFAULT_SHOW_PYTHON is False
    heading, source = visible_code(
        pseudocode=PSEUDO, python_candidate=PYTHON, show_python=DEFAULT_SHOW_PYTHON
    )
    assert heading == "Pseudocode"
    assert source == PSEUDO
    assert "def solve" not in source


def test_toggle_reveals_python_then_returns_to_pseudocode():
    assert toggle_label(False) == "Show Python"
    heading, source = visible_code(
        pseudocode=PSEUDO, python_candidate=PYTHON, show_python=True
    )
    assert heading == "Python implementation"
    assert source == PYTHON
    assert toggle_label(True) == "Show Pseudocode"
    heading, source = visible_code(
        pseudocode=PSEUDO, python_candidate=PYTHON, show_python=False
    )
    assert heading == "Pseudocode"
    assert source == PSEUDO


def test_missing_candidate_cannot_toggle_and_stays_on_pseudocode():
    assert can_toggle_python(None) is False
    assert can_toggle_python("# no function") is False
    assert can_toggle_python(PYTHON) is True
    heading, source = visible_code(
        pseudocode=PSEUDO, python_candidate=None, show_python=True
    )
    assert heading == "Pseudocode"
    assert source == PSEUDO


def test_examples_cover_dp_greedy_graph_and_gate():
    assert "Longest Increasing Subsequence" in EXAMPLES
    assert "Activity selection" in EXAMPLES
    assert "Directed cycle detection" in EXAMPLES
    assert "Underspecified graph (triggers gate)" in EXAMPLES
    assert "graph" in EXAMPLES["Underspecified graph (triggers gate)"].lower()


def test_examples_cover_all_five_added_paradigms():
    """The dropdown must not silently lag behind the paradigms the pipeline
    actually supports -- these five were added after the original six."""
    assert "US coin change (canonical greedy)" in EXAMPLES
    assert "Redundant connection (Union-Find)" in EXAMPLES
    assert "Network delay time (Dijkstra)" in EXAMPLES
    assert "Climbing stairs" in EXAMPLES
    assert "N-Queens count" in EXAMPLES
    assert "Maximum flow" in EXAMPLES
    assert "Two-sum (sort + two pointers)" in EXAMPLES
    assert "Longest common subsequence" in EXAMPLES
    assert "0/1 knapsack" in EXAMPLES
    assert "Topological sort" in EXAMPLES


def test_source_path_label_covers_all_response_paths():
    assert source_path_label("template") == "Offline template"
    assert source_path_label("llm") == "LLM-generated"
    assert source_path_label("stub") == "Unmatched stub"
    assert source_path_label("gated") == "Awaiting clarification"


def test_streamlit_app_uses_view_helpers():
    """The running app must call the tested helpers, not a parallel copy."""
    src = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "app.ui":
            imported.update(alias.name for alias in node.names)
    assert {
        "DEFAULT_SHOW_PYTHON",
        "EXAMPLES",
        "can_toggle_python",
        "toggle_label",
        "visible_code",
        "source_path_label",
    } <= imported
    assert "visible_code(" in src
    assert "toggle_label(" in src
    assert "can_toggle_python(" in src
    assert "source_path_label(" in src

"""Command-line surface: PYTHONPATH=. python -m src \"problem text\"."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from schemas.models import OracleResponse
from src.pipeline import run_oracle


def format_result(result: OracleResponse, *, show_python: bool = False) -> str:
    lines = [
        f"source: {result.source_path}",
        f"profile: {result.profile.input_type} — {result.profile.summary}",
    ]
    if result.needs_clarification:
        lines.append("needs clarification:")
        for item in result.profile.missing_constraints:
            lines.append(f"  - {item}")
        return "\n".join(lines)

    assert result.classification is not None
    assert result.algorithm is not None
    assert result.verification is not None
    assert result.explanation is not None

    c, a, v, e = result.classification, result.algorithm, result.verification, result.explanation
    lines.append(f"paradigm: {c.primary_paradigm_id} ({c.confidence})")
    lines.append(f"rationale: {c.rationale_summary}")
    lines.append(f"complexity: {a.time_complexity} time, {a.space_complexity} space")
    lines.append("pseudocode:")
    lines.append(a.pseudocode)
    if show_python and a.python_candidate:
        lines.append("python:")
        lines.append(a.python_candidate)
    lines.append(f"verification: {v.status} — {v.message}")
    lines.append(f"why ({e.argument_template_used}):")
    lines.append(e.textbook_why)
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="Algorithm Oracle: profile → classify → instantiate → verify → explain.",
    )
    parser.add_argument("problem", nargs="*", help="Problem statement (or pass on stdin)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass the clarification gate",
    )
    parser.add_argument("--json", action="store_true", help="Print OracleResponse JSON")
    parser.add_argument(
        "--python",
        action="store_true",
        help="Include python_candidate when present",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    text = " ".join(args.problem).strip()
    if not text:
        text = sys.stdin.read().strip()
    if not text:
        parser.error("a problem statement is required")

    result = run_oracle(text, force=args.force)
    if args.json:
        print(result.model_dump_json(indent=2))
    else:
        print(format_result(result, show_python=args.python))
    return 0

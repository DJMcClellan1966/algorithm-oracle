#!/usr/bin/env python3
"""
Quick demo of the Phase 2 classifier.

Usage:
  PYTHONPATH=. python scripts/demo_classifier.py
  PYTHONPATH=. python scripts/demo_classifier.py "your problem text here"
"""

from __future__ import annotations
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.classifier import classify_from_text, load_taxonomy


def main():
    if len(sys.argv) > 1:
        problems = [" ".join(sys.argv[1:])]
    else:
        # Default: run the labeled examples
        import json
        with open(ROOT / "examples" / "test_problems.json") as f:
            data = json.load(f)
        problems = [item["problem"] for item in data]

    print(f"Loaded {len(load_taxonomy()['paradigms'])} paradigms from taxonomy\n")

    for i, text in enumerate(problems, 1):
        print("=" * 72)
        print(f"[{i}] {text[:120]}{'...' if len(text) > 120 else ''}")
        result = classify_from_text(text)
        print(f"\n  Primary : {result.primary_paradigm_id}  ({result.primary_paradigm_name})")
        print(f"  Confidence: {result.confidence}")
        print(f"  Rationale : {result.rationale_summary}")
        if result.rejected:
            print("  Rejected :")
            for r in result.rejected:
                print(f"    - {r.paradigm_id}: {r.reason}")
        if result.ambiguities_noted:
            print(f"  Ambiguities: {result.ambiguities_noted}")
        if result.unverified_because:
            print(f"  Note: {result.unverified_because}")
        print()


if __name__ == "__main__":
    main()

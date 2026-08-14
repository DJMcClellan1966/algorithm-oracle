#!/usr/bin/env python3
"""
Full pipeline demo: Profile → Classify → Instantiate → Verify → Explain
"""

from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.pipeline import run_oracle

PROBLEMS = [
    "Given an array of integers, return the length of the longest strictly increasing subsequence.",
    "You are given a list of activities, each with a start time and a finish time. Select the largest possible set of activities so that no two overlap.",
    "Determine whether a directed graph contains a cycle.",
]


def main():
    for i, text in enumerate(PROBLEMS, 1):
        print("=" * 72)
        print(f"[{i}] {text[:90]}{'...' if len(text) > 90 else ''}")
        r = run_oracle(text)
        c, a, v, e = r["classification"], r["algorithm"], r["verification"], r["explanation"]

        print(f"\n  CLASSIFICATION: {c.primary_paradigm_id} ({c.confidence})")
        for rej in c.rejected[:2]:
            print(f"    rejected {rej.paradigm_id}: {rej.reason[:70]}")

        print(f"\n  PSEUDOCODE:\n{a.pseudocode[:300]}")

        print(f"\n  VERIFICATION: {v.status} — {v.message}")

        print(f"\n  WHY ({e.argument_template_used}):")
        # Print first ~8 lines of the explanation
        for line in e.textbook_why.splitlines()[:10]:
            print(f"    {line}")
        if e.why_alternatives_fail:
            print("  Why alternatives fail:")
            for w in e.why_alternatives_fail[:2]:
                print(f"    - {w[:90]}")
        print()


if __name__ == "__main__":
    main()

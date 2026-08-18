#!/usr/bin/env python3
"""
Demo: Profile → Classify → Instantiate → Verify

Runs a few classic problems through the wired stages.
"""

from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.offline_env import isolate_from_llm_env
from src.pipeline import run_oracle


PROBLEMS = [
    "Given an array of integers, return the length of the longest strictly increasing subsequence.",
    "You are given a list of activities, each with a start time and a finish time. Select the largest possible set of activities so that no two overlap.",
    "Determine whether a directed graph contains a cycle.",
    "Sort an array of n integers in O(n log n) time using a divide-and-conquer approach.",
    "Koko can eat bananas at speed k. Given piles and hours h, find the minimum integer k such that she can finish all piles in at most h hours.",
]


def main():
    isolate_from_llm_env()
    for i, text in enumerate(PROBLEMS, 1):
        print("=" * 72)
        print(f"[{i}] {text[:100]}{'...' if len(text) > 100 else ''}")
        result = run_oracle(text)
        c = result.classification
        a = result.algorithm
        v = result.verification

        print(f"\n  Classification : {c.primary_paradigm_id} ({c.confidence})")
        print(f"  Invariant      : {a.loop_invariant_or_key_insight[:100]}...")
        print(f"  Complexity     : {a.time_complexity} time, {a.space_complexity} space")
        print(f"  Has pseudocode : {bool(a.pseudocode)}")
        print(f"  Has candidate  : {bool(a.python_candidate)}")
        print(f"  Has reference  : {bool(a.brute_force_reference)}")
        print(f"  Verification   : {v.status} — {v.message}")
        if v.failed_cases:
            f = v.failed_cases[0]
            print(f"    sample fail  : {f.input_desc!r} exp={f.expected} got={f.actual}")
        print()


if __name__ == "__main__":
    main()

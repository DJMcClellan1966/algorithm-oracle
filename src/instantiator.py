"""
Phase 3 – Instantiator

Given a ProblemProfile + ClassificationResult, produce a ConcreteAlgorithm:
  - loop invariant / key insight first
  - clean pseudocode
  - brute-force reference (Python, def solve)
  - python_candidate (Python, def solve) for verification + UI toggle

Uses LLM + structured output when an API key is present.
Falls back to high-quality hand templates for the classic problems
so the pipeline stays fully testable offline.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from schemas.models import ProblemProfile, ClassificationResult, ConcreteAlgorithm
from src.problem_shapes import detect_shape

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


# ---------------------------------------------------------------------------
# Hand templates for offline / demo use
# ---------------------------------------------------------------------------

def _template_activity_selection() -> ConcreteAlgorithm:
    pseudocode = """\
Sort activities by increasing finish time
result = empty list
last_finish = –infinity

for each activity in sorted list:
    if activity.start ≥ last_finish:
        add activity to result
        last_finish = activity.finish

return result
"""
    candidate = '''\
def solve(activities):
    """activities: list of (start, finish) tuples. Returns selected list."""
    if not activities:
        return []
    ordered = sorted(activities, key=lambda x: x[1])
    result = []
    last_finish = float("-inf")
    for start, finish in ordered:
        if start >= last_finish:
            result.append((start, finish))
            last_finish = finish
    return result
'''
    # Brute force: try all subsets, keep feasible of max size
    reference = '''\
def solve(activities):
    n = len(activities)
    best = []
    for mask in range(1 << n):
        chosen = [activities[i] for i in range(n) if mask & (1 << i)]
        chosen_sorted = sorted(chosen, key=lambda x: x[0])
        ok = all(chosen_sorted[i][1] <= chosen_sorted[i+1][0] for i in range(len(chosen_sorted)-1))
        if ok and len(chosen) > len(best):
            best = chosen
    return sorted(best, key=lambda x: x[1])
'''
    return ConcreteAlgorithm(
        paradigm_id="greedy_exchange",
        loop_invariant_or_key_insight=(
            "After processing the first k activities in finish-time order, "
            "`result` is an optimal selection among those k activities, and "
            "`last_finish` is the finish time of the last selected activity."
        ),
        pseudocode=pseudocode.strip(),
        time_complexity="O(n log n)",
        space_complexity="O(n)",
        brute_force_reference=reference.strip(),
        python_candidate=candidate.strip(),
        notes="Canonical interval scheduling / activity selection.",
    )


def _template_lis() -> ConcreteAlgorithm:
    pseudocode = """\
dp[i] = length of the longest increasing subsequence ending at index i

for i = 0 to n-1:
    dp[i] = 1
    for j = 0 to i-1:
        if A[j] < A[i]:
            dp[i] = max(dp[i], dp[j] + 1)

answer = maximum value in dp
"""
    candidate = '''\
def solve(A):
    if not A:
        return 0
    n = len(A)
    dp = [1] * n
    for i in range(n):
        for j in range(i):
            if A[j] < A[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)
'''
    reference = '''\
def solve(A):
    n = len(A)
    best = 0
    for mask in range(1 << n):
        seq = [A[i] for i in range(n) if mask & (1 << i)]
        if all(seq[i] < seq[i+1] for i in range(len(seq)-1)):
            best = max(best, len(seq))
    return best
'''
    return ConcreteAlgorithm(
        paradigm_id="dp_optimal_substructure",
        loop_invariant_or_key_insight=(
            "After finishing index i, dp[0..i] are correct: dp[k] is the length of the "
            "longest increasing subsequence that ends exactly at k, for every k ≤ i."
        ),
        pseudocode=pseudocode.strip(),
        time_complexity="O(n²)",
        space_complexity="O(n)",
        brute_force_reference=reference.strip(),
        python_candidate=candidate.strip(),
        notes="Classic LIS length. O(n log n) variant exists but is omitted here.",
    )


def _template_directed_cycle() -> ConcreteAlgorithm:
    pseudocode = """\
Color all nodes white (unvisited)

for each node u:
    if u is white:
        if DFS(u) finds a cycle:
            return true
return false

DFS(u):
    color u gray                # on current path
    for each neighbor v of u:
        if v is gray:           # back edge
            return true
        if v is white and DFS(v):
            return true
    color u black               # finished
    return false
"""
    candidate = '''\
def solve(graph):
    """graph: dict node -> list of neighbors. Returns True if a directed cycle exists."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in graph}

    def dfs(u):
        color[u] = GRAY
        for v in graph.get(u, []):
            if color.get(v, WHITE) == GRAY:
                return True
            if color.get(v, WHITE) == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False

    for node in graph:
        if color[node] == WHITE:
            if dfs(node):
                return True
    return False
'''
    # Reference: check every simple path via DFS enumeration (small graphs only)
    reference = '''\
def solve(graph):
    nodes = list(graph.keys())
    def has_cycle_from(start, path, visited_edge):
        for v in graph.get(path[-1], []):
            if v in path:
                return True
            if (path[-1], v) in visited_edge:
                continue
            visited_edge.add((path[-1], v))
            if has_cycle_from(start, path + [v], visited_edge):
                return True
        return False
    for s in nodes:
        if has_cycle_from(s, [s], set()):
            return True
    return False
'''
    return ConcreteAlgorithm(
        paradigm_id="graph_traversal",
        loop_invariant_or_key_insight=(
            "Gray nodes form the current DFS recursion path. A back edge to a gray node "
            "closes a directed cycle. Black nodes are fully processed and cannot participate "
            "in a new cycle with the current path."
        ),
        pseudocode=pseudocode.strip(),
        time_complexity="O(V + E)",
        space_complexity="O(V)",
        brute_force_reference=reference.strip(),
        python_candidate=candidate.strip(),
        notes="DFS three-coloring cycle detection for directed graphs.",
    )


def _template_binary_search_answer() -> ConcreteAlgorithm:
    pseudocode = """\
lo = 1, hi = max(piles)          # search range for speed k
while lo < hi:
    mid = (lo + hi) // 2
    if hours_needed(piles, mid) ≤ h:
        hi = mid                 # mid is feasible
    else:
        lo = mid + 1
return lo

hours_needed(piles, k):
    return sum(ceil(p / k) for p in piles)
"""
    candidate = '''\
def solve(data):
    """data = (piles, h). Returns minimum integer speed k."""
    piles, h = data
    if not piles:
        return 0

    def hours_needed(k):
        return sum((p + k - 1) // k for p in piles)

    lo, hi = 1, max(piles)
    while lo < hi:
        mid = (lo + hi) // 2
        if hours_needed(mid) <= h:
            hi = mid
        else:
            lo = mid + 1
    return lo
'''
    reference = '''\
def solve(data):
    piles, h = data
    if not piles:
        return 0
    def hours_needed(k):
        return sum((p + k - 1) // k for p in piles)
    k = 1
    while hours_needed(k) > h:
        k += 1
    return k
'''
    return ConcreteAlgorithm(
        paradigm_id="binary_search",
        loop_invariant_or_key_insight=(
            "At every step the answer lies in [lo, hi]. If mid is feasible then any larger "
            "speed is also feasible, so the minimum feasible speed is in [lo, mid]; otherwise "
            "it is in [mid+1, hi]."
        ),
        pseudocode=pseudocode.strip(),
        time_complexity="O(n log M) where M = max(piles)",
        space_complexity="O(1)",
        brute_force_reference=reference.strip(),
        python_candidate=candidate.strip(),
        notes="Binary search on the answer (Koko eating bananas style).",
    )


def _template_merge_sort() -> ConcreteAlgorithm:
    pseudocode = """\
function mergesort(A):
    if len(A) ≤ 1: return A
    mid = len(A) // 2
    left = mergesort(A[0..mid))
    right = mergesort(A[mid..n))
    return merge(left, right)

function merge(L, R):
    result = []
    while L and R not empty:
        append the smaller of L[0], R[0] and advance that pointer
    append any remaining elements
    return result
"""
    candidate = '''\
def solve(A):
    if len(A) <= 1:
        return list(A)
    mid = len(A) // 2
    left = solve(A[:mid])
    right = solve(A[mid:])
    return _merge(left, right)

def _merge(L, R):
    result = []
    i = j = 0
    while i < len(L) and j < len(R):
        if L[i] <= R[j]:
            result.append(L[i]); i += 1
        else:
            result.append(R[j]); j += 1
    result.extend(L[i:])
    result.extend(R[j:])
    return result
'''
    reference = '''\
def solve(A):
    return sorted(A)
'''
    return ConcreteAlgorithm(
        paradigm_id="divide_and_conquer",
        loop_invariant_or_key_insight=(
            "After the two recursive calls, left and right are sorted. The merge step "
            "produces a sorted concatenation by always taking the smaller head element."
        ),
        pseudocode=pseudocode.strip(),
        time_complexity="O(n log n)",
        space_complexity="O(n)",
        brute_force_reference=reference.strip(),
        python_candidate=candidate.strip(),
        notes="Classic mergesort.",
    )


def _template_two_sum_sorted() -> ConcreteAlgorithm:
    """Two pointers on a sorted array: find if a pair sums to target (returns bool)."""
    pseudocode = """\
lo = 0, hi = n - 1
while lo < hi:
    s = A[lo] + A[hi]
    if s == target: return true
    if s < target: lo += 1
    else: hi -= 1
return false
"""
    candidate = '''\
def solve(data):
    """data = (A, target). A need not be sorted; we sort a copy."""
    A, target = data
    B = sorted(A)
    lo, hi = 0, len(B) - 1
    while lo < hi:
        s = B[lo] + B[hi]
        if s == target:
            return True
        if s < target:
            lo += 1
        else:
            hi -= 1
    return False
'''
    reference = '''\
def solve(data):
    A, target = data
    n = len(A)
    for i in range(n):
        for j in range(i + 1, n):
            if A[i] + A[j] == target:
                return True
    return False
'''
    return ConcreteAlgorithm(
        paradigm_id="two_pointers_sliding",
        loop_invariant_or_key_insight=(
            "After sorting, if A[lo]+A[hi] < target, every pair using A[lo] with an index < hi "
            "is even smaller, so lo must advance; symmetrically if the sum is too large, hi must decrease."
        ),
        pseudocode=pseudocode.strip(),
        time_complexity="O(n log n) including sort; O(n) two-pointer scan",
        space_complexity="O(n) for the sorted copy",
        brute_force_reference=reference.strip(),
        python_candidate=candidate.strip(),
        notes="Two-sum existence via sort + two pointers.",
    )


def _template_lcs() -> ConcreteAlgorithm:
    pseudocode = """\
dp[i][j] = LCS length of A[0..i) and B[0..j)

for i = 0..n:
    for j = 0..m:
        if i == 0 or j == 0: dp[i][j] = 0
        else if A[i-1] == B[j-1]: dp[i][j] = dp[i-1][j-1] + 1
        else: dp[i][j] = max(dp[i-1][j], dp[i][j-1])

answer = dp[n][m]
"""
    candidate = '''\
def solve(data):
    """data = (A, B) sequences (lists or strings). Returns LCS length."""
    A, B = data
    n, m = len(A), len(B)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if A[i - 1] == B[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[n][m]
'''
    reference = '''\
def solve(data):
    A, B = data
    n, m = len(A), len(B)
    best = 0
    # enumerate subsequences of A via bitmasks (n small)
    for mask in range(1 << n):
        seq = [A[i] for i in range(n) if mask & (1 << i)]
        # check if seq is subsequence of B
        k = 0
        for x in B:
            if k < len(seq) and x == seq[k]:
                k += 1
        if k == len(seq):
            best = max(best, len(seq))
    return best
'''
    return ConcreteAlgorithm(
        paradigm_id="dp_optimal_substructure",
        loop_invariant_or_key_insight=(
            "dp[i][j] is the LCS length of the prefixes A[0..i) and B[0..j). "
            "When the last characters match they both contribute; otherwise the answer is the "
            "better of dropping A[i-1] or dropping B[j-1]."
        ),
        pseudocode=pseudocode.strip(),
        time_complexity="O(n m)",
        space_complexity="O(n m)",
        brute_force_reference=reference.strip(),
        python_candidate=candidate.strip(),
        notes="Longest Common Subsequence length. Brute force only for tiny n.",
    )


def _template_knapsack_01() -> ConcreteAlgorithm:
    pseudocode = """\
dp[i][w] = max value using first i items with capacity w

for i = 1..n:
    for w = 0..W:
        dp[i][w] = dp[i-1][w]
        if weight[i] <= w:
            dp[i][w] = max(dp[i][w], dp[i-1][w - weight[i]] + value[i])

answer = dp[n][W]
"""
    candidate = '''\
def solve(data):
    """data = (weights, values, W). 0/1 knapsack max value."""
    weights, values, W = data
    n = len(weights)
    dp = [0] * (W + 1)
    for i in range(n):
        wi, vi = weights[i], values[i]
        for w in range(W, wi - 1, -1):
            dp[w] = max(dp[w], dp[w - wi] + vi)
    return dp[W]
'''
    reference = '''\
def solve(data):
    weights, values, W = data
    n = len(weights)
    best = 0
    for mask in range(1 << n):
        tw = tv = 0
        for i in range(n):
            if mask & (1 << i):
                tw += weights[i]
                tv += values[i]
        if tw <= W:
            best = max(best, tv)
    return best
'''
    return ConcreteAlgorithm(
        paradigm_id="dp_optimal_substructure",
        loop_invariant_or_key_insight=(
            "After considering the first i items, dp[w] is the maximum value achievable "
            "with capacity exactly ≤ w. Each item is considered once (0/1), updating the table "
            "from high capacity to low so that an item is never reused."
        ),
        pseudocode=pseudocode.strip(),
        time_complexity="O(n W)",
        space_complexity="O(W)",
        brute_force_reference=reference.strip(),
        python_candidate=candidate.strip(),
        notes="0/1 knapsack. Verification uses small n and W.",
    )


def _template_topo_sort() -> ConcreteAlgorithm:
    pseudocode = """\
Compute in-degree of every node
Queue all nodes with in-degree 0
result = []
while queue not empty:
    u = pop queue
    append u to result
    for each neighbor v of u:
        in-degree[v] -= 1
        if in-degree[v] == 0: push v

if len(result) == |V|: return result  # valid topo order
else: return None  # cycle exists
"""
    candidate = '''\
def solve(graph):
    """graph: dict node -> list of neighbors (directed). Returns a topo order or None if cycle."""
    nodes = list(graph.keys())
    indeg = {u: 0 for u in nodes}
    for u in nodes:
        for v in graph.get(u, []):
            if v not in indeg:
                indeg[v] = 0
                nodes.append(v)
            indeg[v] += 1
    from collections import deque
    q = deque([u for u in indeg if indeg[u] == 0])
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in graph.get(u, []):
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    if len(order) != len(indeg):
        return None
    return order
'''
    reference = '''\
def solve(graph):
    # Brute: try all permutations of nodes; return first valid topo order or None
    nodes = list(dict.fromkeys([*graph.keys(), *[v for u in graph for v in graph[u]]]))
    n = len(nodes)
    if n > 7:
        # fall back: use Kahn-like for large (should not happen in tests)
        return None
    import itertools
    pos = {nodes[i]: i for i in range(n)}
    for perm in itertools.permutations(nodes):
        rank = {perm[i]: i for i in range(n)}
        ok = True
        for u in graph:
            for v in graph[u]:
                if rank[u] >= rank[v]:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            return list(perm)
    return None
'''
    return ConcreteAlgorithm(
        paradigm_id="graph_traversal",
        loop_invariant_or_key_insight=(
            "Nodes in the queue have all predecessors already placed in the order. "
            "Each emitted node has in-degree 0 relative to the remaining graph. "
            "If a cycle exists, fewer than |V| nodes are emitted."
        ),
        pseudocode=pseudocode.strip(),
        time_complexity="O(V + E)",
        space_complexity="O(V)",
        brute_force_reference=reference.strip(),
        python_candidate=candidate.strip(),
        notes="Kahn's algorithm for topological sort; None if cycle.",
    )


def _template_redundant_connection() -> ConcreteAlgorithm:
    reference = '''\
def solve(edges):
    adj = {}
    def connected(a, b):
        if a == b:
            return True
        seen = {a}
        stack = [a]
        while stack:
            cur = stack.pop()
            for nxt in adj.get(cur, []):
                if nxt == b:
                    return True
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return False
    for u, v in edges:
        if connected(u, v):
            return [u, v]
        adj.setdefault(u, []).append(v)
        adj.setdefault(v, []).append(u)
    return None
'''
    candidate = '''\
def solve(edges):
    parent = {}
    rank = {}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return False
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1
        return True
    for u, v in edges:
        if u not in parent:
            parent[u], rank[u] = u, 0
        if v not in parent:
            parent[v], rank[v] = v, 0
        if not union(u, v):
            return [u, v]
    return None
'''
    return ConcreteAlgorithm(
        paradigm_id="union_find",
        loop_invariant_or_key_insight=(
            "After processing a prefix of edges, two nodes are in the same Union-Find set "
            "if and only if they are connected using only edges from that prefix. The input "
            "is a tree (n-1 edges) plus one extra edge, so exactly one edge -- processed in "
            "the given order -- finds its endpoints already connected; that edge is the answer."
        ),
        pseudocode="""\
function solve(edges):
    parent = {}, rank = {}
    for (u, v) in edges:
        register u, v as singleton sets if new
        if find(u) == find(v):
            return [u, v]      # this edge closes the one cycle
        union(u, v)
    return None                # unreachable for a valid tree+1-edge input
""",
        time_complexity="O(n α(n)) with union by rank + path compression",
        space_complexity="O(n)",
        brute_force_reference=reference.strip(),
        python_candidate=candidate.strip(),
        notes="Union-Find (redundant connection) template.",
    )


TEMPLATES = {
    "redundant_connection": _template_redundant_connection,
    "activity": _template_activity_selection,
    "lis": _template_lis,
    "cycle": _template_directed_cycle,
    "koko": _template_binary_search_answer,
    "mergesort": _template_merge_sort,
    "two_sum": _template_two_sum_sorted,
    "lcs": _template_lcs,
    "knapsack": _template_knapsack_01,
    "topo": _template_topo_sort,
}


def _match_template(profile: ProblemProfile, classification: ClassificationResult) -> Optional[ConcreteAlgorithm]:
    text = profile.summary + " " + classification.primary_paradigm_id
    shape = detect_shape(text)
    factory = TEMPLATES.get(shape)
    return factory() if factory else None


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------

def _llm_instantiate(
    profile: ProblemProfile,
    classification: ClassificationResult,
    model: str = "gpt-4o",
) -> ConcreteAlgorithm:
    import instructor
    from openai import OpenAI

    system = (PROMPTS_DIR / "instantiator_system.txt").read_text(encoding="utf-8")
    # Strengthen the prompt so both executable sources are required
    system += """

Additional hard requirements:
- brute_force_reference MUST be a complete Python function named `solve` that is obviously correct (may be exponential).
- python_candidate MUST be a complete Python function named `solve` implementing the efficient algorithm.
- Both functions must accept the same input shape.
- loop_invariant_or_key_insight must be stated before you write pseudocode.
- Do not change the paradigm_id; copy it from the classification.
"""

    user = f"""Problem profile:
{profile.model_dump_json(indent=2)}

Classification (FIXED – do not change the paradigm):
{classification.model_dump_json(indent=2)}

Produce a ConcreteAlgorithm JSON object.
"""

    client = instructor.from_openai(OpenAI())
    result = client.chat.completions.create(
        model=model,
        response_model=ConcreteAlgorithm,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    # Ensure paradigm_id matches classification
    result.paradigm_id = classification.primary_paradigm_id
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def instantiate(
    profile: ProblemProfile,
    classification: ClassificationResult,
    *,
    model: str = "gpt-4o",
    use_mock_if_no_key: bool = True,
) -> ConcreteAlgorithm:
    """
    Main entry point for Phase 3.
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            return _llm_instantiate(profile, classification, model=model)
        except Exception as e:
            if not use_mock_if_no_key:
                raise
            print(f"[instantiator] LLM call failed ({e}); falling back to template")

    templated = _match_template(profile, classification)
    if templated is not None:
        return templated

    # Last-resort minimal stub so the pipeline does not crash
    return ConcreteAlgorithm(
        paradigm_id=classification.primary_paradigm_id,
        loop_invariant_or_key_insight="(No template matched – real LLM required for this problem.)",
        pseudocode="# TODO: no offline template for this problem/paradigm combination",
        time_complexity="unknown",
        space_complexity="unknown",
        brute_force_reference=None,
        python_candidate=None,
        notes="Fallback stub. Provide OPENAI_API_KEY or add a template.",
    )

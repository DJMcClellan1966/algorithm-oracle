"""
Executable verification harness for Algorithm Oracle.

Capabilities:
- Compile Python source strings into callables (restricted globals)
- Generate random + adversarial inputs
- Differential testing: candidate vs brute-force reference
- Return a structured VerificationReport
- Optional crude empirical timing probe

Safety notes:
- Uses a restricted globals dict (no builtins that can touch the filesystem/network).
- Still not a full sandbox — do not feed untrusted code from the public internet
  without an OS-level container. Adequate for local / trusted LLM output.
"""

from __future__ import annotations

import multiprocessing
import random
import time
import traceback
from collections import Counter
from typing import Any, Callable, List, Optional, Tuple

from schemas.models import TestCaseResult, VerificationReport

# Wall-clock budget for one candidate/reference call when running from source.
# None disables the process wrapper (in-process callables, no kill).
DEFAULT_CALL_TIMEOUT_S = 5.0


# ---------------------------------------------------------------------------
# Restricted execution
# ---------------------------------------------------------------------------

# Minimal safe builtins for pure algorithmic functions
_SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "frozenset": frozenset,
    "int": int,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "print": print,  # useful for debugging generated code; remove later if desired
    "range": range,
    "reversed": reversed,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    "True": True,
    "False": False,
    "None": None,
}


def compile_function(
    source: str,
    function_name: str = "solve",
    timeout_hint: str = "Keep functions pure and terminating on small inputs.",
) -> Callable:
    """
    Compile a Python source string and return the named function.

    The source should define a top-level function (default name: `solve`).
    Raises ValueError if the function is missing or compilation fails.
    """
    if not source or not source.strip():
        raise ValueError("Empty source code")

    globals_dict: dict[str, Any] = {"__builtins__": _SAFE_BUILTINS}
    locals_dict: dict[str, Any] = {}

    try:
        exec(compile(source, "<algorithm_oracle>", "exec"), globals_dict, locals_dict)
    except Exception as e:
        raise ValueError(f"Failed to compile source: {type(e).__name__}: {e}") from e

    # Merge locals into globals so recursive calls and helpers resolve
    globals_dict.update(locals_dict)

    fn = globals_dict.get(function_name)
    if fn is None or not callable(fn):
        available = [
            k for k, v in globals_dict.items()
            if callable(v) and not k.startswith("_")
        ]
        raise ValueError(
            f"Function '{function_name}' not found after exec. "
            f"Callables found: {available or '(none)'}"
        )

    # Ensure the function's global namespace includes itself and helpers
    # (needed for recursion and sibling defs like _merge)
    if hasattr(fn, "__globals__"):
        fn.__globals__.update(globals_dict)

    return fn


def _compile_fail_report(exc: ValueError) -> VerificationReport:
    return VerificationReport(
        status="failed",
        message=f"Compilation error: {exc}",
        failed_cases=[
            TestCaseResult(
                input_desc="(compile)",
                expected="successful compile",
                actual=str(exc),
                passed=False,
            )
        ],
    )


def _timed_eval_server(source: str, function_name: str, in_conn, out_conn) -> None:
    """Child process: compile once, then eval inputs until the pipe closes."""
    try:
        fn = compile_function(source, function_name)
        while True:
            try:
                inp = in_conn.recv()
            except EOFError:
                break
            try:
                out_conn.send(("ok", fn(inp)))
            except Exception as e:
                out_conn.send(("err", type(e).__name__, str(e)))
    finally:
        try:
            in_conn.close()
        except OSError:
            pass
        try:
            out_conn.close()
        except OSError:
            pass


class _TimedSourceCaller:
    """Compile `source` in a spawn-child and kill it if a call exceeds timeout_s."""

    def __init__(self, source: str, function_name: str, timeout_s: float):
        self.source = source
        self.function_name = function_name
        self.timeout_s = timeout_s
        self._ctx = multiprocessing.get_context("spawn")
        self._proc = None
        self._parent_send = None
        self._parent_recv = None
        self._start()

    def _start(self) -> None:
        self.close()
        child_recv, parent_send = self._ctx.Pipe(duplex=False)
        parent_recv, child_send = self._ctx.Pipe(duplex=False)
        self._parent_send = parent_send
        self._parent_recv = parent_recv
        self._proc = self._ctx.Process(
            target=_timed_eval_server,
            args=(self.source, self.function_name, child_recv, child_send),
        )
        self._proc.start()
        child_recv.close()
        child_send.close()

    def call(self, inp: Any) -> Any:
        if self._proc is None or not self._proc.is_alive():
            self._start()
        try:
            self._parent_send.send(inp)
        except (BrokenPipeError, OSError, EOFError):
            self._start()
            self._parent_send.send(inp)
        if self._parent_recv.poll(self.timeout_s):
            msg = self._parent_recv.recv()
            if msg[0] == "ok":
                return msg[1]
            raise RuntimeError(f"{msg[1]}: {msg[2]}")
        self.close()
        raise TimeoutError(f"solve exceeded {self.timeout_s}s")

    def close(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is not None and proc.is_alive():
            proc.terminate()
            proc.join(1)
            if proc.is_alive():
                proc.kill()
                proc.join(1)
        for conn in (self._parent_send, self._parent_recv):
            if conn is not None:
                try:
                    conn.close()
                except OSError:
                    pass
        self._parent_send = None
        self._parent_recv = None


def _solvers_from_source(
    candidate_source: str,
    reference_source: str,
    function_name: str,
    call_timeout_s: Optional[float],
) -> Tuple[Optional[Callable], Optional[Callable], Callable[[], None], Optional[VerificationReport]]:
    """Compile-check both sources. On success, return callables plus a cleanup hook."""
    try:
        inproc_c = compile_function(candidate_source, function_name)
        inproc_r = compile_function(reference_source, function_name)
    except ValueError as e:
        return None, None, lambda: None, _compile_fail_report(e)
    if call_timeout_s is None:
        return inproc_c, inproc_r, lambda: None, None
    cand = _TimedSourceCaller(candidate_source, function_name, call_timeout_s)
    ref = _TimedSourceCaller(reference_source, function_name, call_timeout_s)
    return cand.call, ref.call, lambda: (cand.close(), ref.close()), None


def _interval_pair(item: Any) -> Optional[tuple]:
    if isinstance(item, (list, tuple)) and len(item) == 2:
        return (item[0], item[1])
    return None


def _is_feasible_activity_selection(intervals: Any, selected: Any) -> bool:
    """True iff selected is a non-overlapping submultiset of intervals.

    Touching endpoints (finish == next start) are allowed, matching the
    activity-selection template's `start >= last_finish` rule.
    """
    if not isinstance(selected, (list, tuple)):
        return False
    normalized: list[tuple] = []
    for item in selected:
        pair = _interval_pair(item)
        if pair is None:
            return False
        normalized.append(pair)
    available = Counter(
        p for p in (_interval_pair(x) for x in intervals) if p is not None
    )
    used = Counter(normalized)
    for iv, cnt in used.items():
        if cnt > available.get(iv, 0):
            return False
    ordered = sorted(normalized, key=lambda x: (x[0], x[1]))
    for i in range(len(ordered) - 1):
        if ordered[i][1] > ordered[i + 1][0]:
            return False
    return True


def _is_valid_topological_order(graph: Any, order: Any) -> bool:
    """True iff order is a permutation of the graph's nodes and respects every edge."""
    if not isinstance(order, (list, tuple)) or not isinstance(graph, dict):
        return False
    nodes = list(
        dict.fromkeys(
            [*graph.keys(), *[v for u in graph for v in graph.get(u, [])]]
        )
    )
    if len(order) != len(nodes) or set(order) != set(nodes):
        return False
    rank = {node: i for i, node in enumerate(order)}
    for u in graph:
        for v in graph.get(u, []):
            if rank[u] >= rank[v]:
                return False
    return True


def _normalize_activity_output(inp: Any, out: Any) -> Any:
    if not isinstance(out, (list, tuple)):
        return out
    return (_is_feasible_activity_selection(inp, out), len(out))


def _normalize_graph_output(inp: Any, out: Any) -> Any:
    if isinstance(out, (list, tuple)):
        return ("order", _is_valid_topological_order(inp, out), len(out))
    return out


# ---------------------------------------------------------------------------
# Input generation
# ---------------------------------------------------------------------------

def generate_random_array(n: int, low: int = 0, high: int = 50) -> list[int]:
    return [random.randint(low, high) for _ in range(n)]



def generate_adversarial_arrays() -> list[dict]:
    return [
        {"desc": "empty", "input": []},
        {"desc": "single element", "input": [42]},
        {"desc": "two equal", "input": [7, 7]},
        {"desc": "already sorted", "input": [1, 2, 3, 4, 5]},
        {"desc": "reverse sorted", "input": [5, 4, 3, 2, 1]},
        {"desc": "all identical", "input": [9, 9, 9, 9]},
        {"desc": "negatives mixed", "input": [-3, -1, 0, 2, -5]},
        {"desc": "duplicates scattered", "input": [3, 1, 3, 2, 1]},
    ]


def generate_random_intervals(n: int, time_max: int = 40) -> list[tuple[int, int]]:
    """List of (start, finish) with start < finish."""
    intervals = []
    for _ in range(n):
        s = random.randint(0, time_max - 1)
        f = random.randint(s + 1, time_max)
        intervals.append((s, f))
    return intervals


def generate_adversarial_intervals() -> list[dict]:
    return [
        {"desc": "empty", "input": []},
        {"desc": "single", "input": [(0, 5)]},
        {"desc": "all overlap", "input": [(0, 10), (1, 9), (2, 8)]},
        {"desc": "chain no overlap", "input": [(0, 1), (1, 2), (2, 3), (3, 4)]},
        {"desc": "nested", "input": [(0, 10), (2, 5), (3, 4)]},
        {"desc": "two disjoint groups", "input": [(0, 2), (1, 3), (10, 12), (11, 13)]},
    ]


def generate_random_digraph(n: int, edge_prob: float = 0.3) -> dict:
    """Adjacency list on nodes 0..n-1."""
    g = {i: [] for i in range(n)}
    for u in range(n):
        for v in range(n):
            if u != v and random.random() < edge_prob:
                g[u].append(v)
    return g


def generate_adversarial_digraphs() -> list[dict]:
    return [
        {"desc": "empty", "input": {}},
        {"desc": "single node", "input": {0: []}},
        {"desc": "self-loop", "input": {0: [0]}},
        {"desc": "mutual edge", "input": {0: [1], 1: [0]}},
        {"desc": "simple DAG", "input": {0: [1], 1: [2], 2: []}},
        {"desc": "triangle cycle", "input": {0: [1], 1: [2], 2: [0]}},
        {"desc": "disconnected cycle", "input": {0: [1], 1: [0], 2: [3], 3: []}},
    ]


def generate_random_koko(n_piles: int = 4, max_pile: int = 20, max_h_factor: int = 3) -> tuple:
    piles = [random.randint(1, max_pile) for _ in range(max(1, n_piles))]
    # h at least n_piles so k=max is always feasible; upper bound a bit larger
    h = random.randint(len(piles), len(piles) * max_h_factor + max(piles))
    return (piles, h)


def generate_adversarial_koko() -> list[dict]:
    return [
        {"desc": "single pile", "input": ([7], 3)},
        {"desc": "all ones", "input": ([1, 1, 1, 1], 4)},
        {"desc": "tight h", "input": ([10, 10], 2)},
        {"desc": "generous h", "input": ([3, 6, 7], 100)},
    ]


def generate_random_pairs(n: int = 6) -> tuple:
    """(A, target) for two-sum / two-pointer problems."""
    A = [random.randint(-20, 20) for _ in range(n)]
    target = random.randint(-30, 30)
    return (A, target)


def generate_adversarial_pairs() -> list[dict]:
    return [
        {"desc": "empty", "input": ([], 0)},
        {"desc": "single", "input": ([5], 5)},
        {"desc": "pair hit", "input": ([1, 4, 7], 5)},
        {"desc": "pair miss", "input": ([1, 4, 7], 100)},
        {"desc": "negatives", "input": ([-3, -1, 2], -4)},
    ]


def generate_random_tree_plus_edge(n: int) -> list[tuple[int, int]]:
    """n nodes (n clamped to >= 3): a random spanning tree's edges plus one
    extra edge closing exactly one cycle, order shuffled."""
    n = max(3, n)
    nodes = list(range(1, n + 1))
    random.shuffle(nodes)
    edges = []
    for i in range(1, n):
        parent = nodes[random.randint(0, i - 1)]
        edges.append((parent, nodes[i]))
    existing = {frozenset(e) for e in edges}
    for _ in range(50):
        a, b = random.sample(nodes, 2)
        if frozenset((a, b)) not in existing:
            edges.append((a, b))
            break
    else:
        edges.append((nodes[0], nodes[1]))
    random.shuffle(edges)
    return edges


def generate_adversarial_tree_plus_edge() -> list[dict]:
    return [
        {"desc": "minimal triangle", "input": [(1, 2), (1, 3), (2, 3)]},
        {"desc": "chain closed into a loop", "input": [(1, 2), (2, 3), (3, 4), (4, 5), (1, 5)]},
        {"desc": "star plus one shortcut edge", "input": [(1, 2), (1, 3), (1, 4), (1, 5), (2, 3)]},
    ]


def generate_random_weighted_digraph(n: int, edge_prob: float = 0.4, max_weight: int = 10) -> tuple:
    """(n, times, k): n nodes labeled 1..n, times = list of (u, v, w) directed
    edges with non-negative integer weights, k = a random source node."""
    n = max(1, n)
    times = []
    for u in range(1, n + 1):
        for v in range(1, n + 1):
            if u != v and random.random() < edge_prob:
                times.append((u, v, random.randint(1, max_weight)))
    k = random.randint(1, n)
    return (n, times, k)


def generate_random_stair_count(max_n: int = 12) -> int:
    return random.randint(0, max_n)


def generate_random_queens_count(max_n: int = 7) -> int:
    return random.randint(0, max_n)


def generate_random_lcs_pair(max_len: int = 6, alphabet_size: int = 5) -> tuple:
    """(A, B): two sequences of small integers for LCS -- dp_optimal_substructure
    shares its paradigm_id with plain-array DP, so this needs its own dispatch
    keyed by shape, not paradigm_id."""
    n, m = random.randint(0, max_len), random.randint(0, max_len)
    A = [random.randint(0, alphabet_size - 1) for _ in range(n)]
    B = [random.randint(0, alphabet_size - 1) for _ in range(m)]
    return (A, B)


def generate_adversarial_lcs_pairs() -> list[dict]:
    return [
        {"desc": "both empty", "input": ([], [])},
        {"desc": "single identical element", "input": ([1], [1])},
        {"desc": "partial overlap", "input": ([1, 2, 3], [1, 3])},
        {"desc": "reversed vs sorted", "input": ([3, 2, 1], [1, 2, 3])},
    ]


def generate_random_knapsack(
    max_items: int = 5, max_weight: int = 8, max_value: int = 10, max_capacity: int = 15
) -> tuple:
    """(weights, values, W) for 0/1 knapsack -- same dp_optimal_substructure
    paradigm_id as plain-array DP and LCS, so this also needs shape-based
    dispatch rather than paradigm_id alone."""
    n = random.randint(0, max_items)
    weights = [random.randint(1, max_weight) for _ in range(n)]
    values = [random.randint(1, max_value) for _ in range(n)]
    W = random.randint(0, max_capacity)
    return (weights, values, W)


def generate_adversarial_knapsacks() -> list[dict]:
    return [
        {"desc": "no items", "input": ([], [], 0)},
        {"desc": "single item, zero capacity", "input": ([1], [5], 0)},
        {"desc": "two items, tight capacity", "input": ([2, 3], [3, 4], 5)},
        {"desc": "item heavier than capacity", "input": ([5], [10], 4)},
    ]


def generate_random_flow_network(n: int, edge_prob: float = 0.5, max_cap: int = 10) -> tuple:
    """(n, edges, s, t): n nodes labeled 1..n, edges = list of (u, v, cap)
    directed edges with positive integer capacities, s=1, t=n."""
    n = max(2, n)
    edges = []
    for u in range(1, n + 1):
        for v in range(1, n + 1):
            if u != v and random.random() < edge_prob:
                edges.append((u, v, random.randint(1, max_cap)))
    return (n, edges, 1, n)


def generate_adversarial_flow_networks() -> list[dict]:
    return [
        {"desc": "no edges", "input": (2, [], 1, 2)},
        {"desc": "direct edge only", "input": (2, [(1, 2, 5)], 1, 2)},
        {"desc": "single bottleneck", "input": (3, [(1, 2, 10), (2, 3, 2)], 1, 3)},
        {"desc": "two parallel paths", "input": (4, [(1, 2, 3), (2, 4, 3), (1, 3, 2), (3, 4, 2)], 1, 4)},
        {"desc": "parallel edges same pair", "input": (2, [(1, 2, 3), (1, 2, 4)], 1, 2)},
        {"desc": "source equals sink", "input": (1, [], 1, 1)},
        {"desc": "disconnected sink", "input": (3, [(1, 2, 5)], 1, 3)},
        {"desc": "diamond shared bottleneck", "input": (4, [(1, 2, 10), (1, 3, 10), (2, 4, 4), (3, 4, 4)], 1, 4)},
        {"desc": "self-loop ignored", "input": (2, [(1, 1, 5), (1, 2, 3)], 1, 2)},
        {"desc": "chain", "input": (5, [(1, 2, 4), (2, 3, 4), (3, 4, 4), (4, 5, 4)], 1, 5)},
    ]


def generate_adversarial_queens_counts() -> list[dict]:
    return [
        {"desc": "n=2, provably no solution", "input": 2},
    ]


def generate_adversarial_stair_counts() -> list[dict]:
    return [
        {"desc": "zero steps", "input": 0},
        {"desc": "one step", "input": 1},
    ]


def generate_adversarial_weighted_digraphs() -> list[dict]:
    return [
        {"desc": "single node", "input": (1, [], 1)},
        {"desc": "unreachable node", "input": (3, [(1, 2, 5)], 1)},
        {"desc": "self-loop ignored", "input": (2, [(1, 1, 3), (1, 2, 4)], 1)},
        {"desc": "chain", "input": (4, [(1, 2, 1), (2, 3, 1), (3, 4, 1)], 1)},
        {"desc": "two paths, cheaper wins", "input": (3, [(1, 2, 10), (1, 3, 1), (3, 2, 1)], 1)},
        {"desc": "disconnected pair", "input": (2, [], 1)},
        {"desc": "star from source", "input": (4, [(1, 2, 2), (1, 3, 5), (1, 4, 1)], 1)},
        {"desc": "zero-weight edge", "input": (2, [(1, 2, 0)], 1)},
        {"desc": "cycle with equal-cost alternative", "input": (3, [(1, 2, 2), (2, 3, 2), (1, 3, 4)], 1)},
    ]


# ---------------------------------------------------------------------------
# Differential testing

# ---------------------------------------------------------------------------

def differential_test(
    candidate: Callable,
    reference: Callable,
    inputs: List[Any],
    input_descs: Optional[List[str]] = None,
) -> Tuple[int, List[TestCaseResult]]:
    failed: List[TestCaseResult] = []
    passed = 0
    descs = input_descs or [repr(x)[:60] for x in inputs]

    for inp, desc in zip(inputs, descs):
        try:
            expected = reference(inp)
        except Exception as e:
            failed.append(
                TestCaseResult(
                    input_desc=desc,
                    expected=f"reference raised {type(e).__name__}: {e}",
                    actual="(not run)",
                    passed=False,
                )
            )
            continue

        try:
            actual = candidate(inp)
            if actual == expected:
                passed += 1
            else:
                failed.append(
                    TestCaseResult(
                        input_desc=desc,
                        expected=expected,
                        actual=actual,
                        passed=False,
                    )
                )
        except Exception as e:
            failed.append(
                TestCaseResult(
                    input_desc=desc,
                    expected=expected,
                    actual=f"raised {type(e).__name__}: {e}",
                    passed=False,
                )
            )
    return passed, failed


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------

def run_verification(
    candidate: Callable,
    reference: Callable,
    *,
    random_n_range: Tuple[int, int] = (0, 10),
    num_random: int = 25,
    include_adversarial: bool = True,
) -> VerificationReport:
    """
    Compare candidate against reference on random + adversarial array inputs.
    Suitable for problems whose signature is roughly `solve(list[int]) -> ...`.
    """
    random_inputs = [
        generate_random_array(random.randint(*random_n_range)) for _ in range(num_random)
    ]
    passed_r, failed_r = differential_test(candidate, reference, random_inputs)

    passed_a, failed_a = 0, []
    num_adv = 0
    if include_adversarial:
        adv = generate_adversarial_arrays()
        num_adv = len(adv)
        passed_a, failed_a = differential_test(
            candidate,
            reference,
            [c["input"] for c in adv],
            [c["desc"] for c in adv],
        )

    total_tests = num_random + num_adv
    total_passed = passed_r + passed_a
    all_failed = failed_r + failed_a

    if all_failed:
        status = "failed"
        msg = f"Failed {len(all_failed)} / {total_tests} tests"
    else:
        status = "passed"
        msg = f"Passed all {total_tests} tests (random + adversarial)"

    return VerificationReport(
        status=status,
        num_random_tests=num_random,
        num_adversarial_tests=num_adv,
        passed_count=total_passed,
        failed_cases=all_failed,
        message=msg,
    )


def run_verification_from_source(
    candidate_source: str,
    reference_source: str,
    *,
    function_name: str = "solve",
    call_timeout_s: Optional[float] = DEFAULT_CALL_TIMEOUT_S,
    **kwargs,
) -> VerificationReport:
    """
    Compile both sources then run differential testing.
    This is the entry point the pipeline will usually call.
    """
    candidate, reference, cleanup, err = _solvers_from_source(
        candidate_source, reference_source, function_name, call_timeout_s
    )
    if err is not None:
        return err
    try:
        return run_verification(candidate, reference, **kwargs)
    finally:
        cleanup()


def run_verification_for_paradigm(
    candidate_source: str,
    reference_source: str,
    paradigm_id: str,
    *,
    function_name: str = "solve",
    num_random: int = 20,
    call_timeout_s: Optional[float] = DEFAULT_CALL_TIMEOUT_S,
) -> VerificationReport:
    """
    Choose input generators based on paradigm / problem shape, then differentially test.
    """
    candidate, reference, cleanup, err = _solvers_from_source(
        candidate_source, reference_source, function_name, call_timeout_s
    )
    if err is not None:
        return err

    try:
        # --- select generators ---
        if paradigm_id == "greedy_exchange":
            random_inputs = [generate_random_intervals(random.randint(0, 8)) for _ in range(num_random)]
            adv = generate_adversarial_intervals()

            def wrap(fn):
                def _inner(inp):
                    out = fn(inp)
                    return _normalize_activity_output(inp, out)
                return _inner

            candidate, reference = wrap(candidate), wrap(reference)
        elif paradigm_id == "graph_traversal":
            random_inputs = [generate_random_digraph(random.randint(0, 5), 0.25) for _ in range(num_random)]
            adv = generate_adversarial_digraphs()

            def wrap_topo_or_cycle(fn):
                def _inner(inp):
                    out = fn(inp)
                    return _normalize_graph_output(inp, out)
                return _inner

            candidate, reference = wrap_topo_or_cycle(candidate), wrap_topo_or_cycle(reference)
        elif paradigm_id == "binary_search":
            random_inputs = [generate_random_koko(random.randint(1, 5)) for _ in range(num_random)]
            adv = generate_adversarial_koko()
        elif paradigm_id == "two_pointers_sliding":
            random_inputs = [generate_random_pairs(random.randint(0, 10)) for _ in range(num_random)]
            adv = generate_adversarial_pairs()
        elif paradigm_id == "union_find":
            random_inputs = [generate_random_tree_plus_edge(random.randint(3, 8)) for _ in range(num_random)]
            adv = generate_adversarial_tree_plus_edge()
        elif paradigm_id == "shortest_path":
            random_inputs = [generate_random_weighted_digraph(random.randint(1, 6)) for _ in range(num_random)]
            adv = generate_adversarial_weighted_digraphs()
        elif paradigm_id == "math_formula":
            random_inputs = [generate_random_stair_count() for _ in range(num_random)]
            adv = generate_adversarial_stair_counts()
        elif paradigm_id == "backtracking":
            random_inputs = [generate_random_queens_count() for _ in range(num_random)]
            adv = generate_adversarial_queens_counts()
        elif paradigm_id == "network_flow":
            random_inputs = [generate_random_flow_network(random.randint(2, 6)) for _ in range(num_random)]
            adv = generate_adversarial_flow_networks()
        else:
            return run_verification(
                candidate, reference, random_n_range=(0, 8), num_random=num_random
            )

        passed_r, failed_r = differential_test(candidate, reference, random_inputs)
        passed_a, failed_a = differential_test(
            candidate, reference, [c["input"] for c in adv], [c["desc"] for c in adv]
        )
        total = num_random + len(adv)
        total_passed = passed_r + passed_a
        failed = failed_r + failed_a
        if failed:
            return VerificationReport(
                status="failed",
                num_random_tests=num_random,
                num_adversarial_tests=len(adv),
                passed_count=total_passed,
                failed_cases=failed,
                message=f"Failed {len(failed)} / {total} tests",
            )
        return VerificationReport(
            status="passed",
            num_random_tests=num_random,
            num_adversarial_tests=len(adv),
            passed_count=total_passed,
            failed_cases=[],
            message=f"Passed all {total} tests (random + adversarial)",
        )
    finally:
        cleanup()


def run_verification_for_shape(
    candidate_source: str,
    reference_source: str,
    shape: Optional[str],
    paradigm_id: str,
    *,
    function_name: str = "solve",
    num_random: int = 15,
    call_timeout_s: Optional[float] = DEFAULT_CALL_TIMEOUT_S,
) -> VerificationReport:
    """
    Some paradigm ids cover more than one input shape -- dp_optimal_substructure
    spans plain-array DP, LCS pairs, and 0/1 knapsack tuples -- so paradigm_id
    alone isn't enough to pick the right generator. Route by the finer-grained
    shape (from src.problem_shapes.detect_shape) first; fall back to
    run_verification_for_paradigm for any shape with no special case.
    """
    if shape == "lcs":
        adv = generate_adversarial_lcs_pairs()
        random_gen = generate_random_lcs_pair
    elif shape == "knapsack":
        adv = generate_adversarial_knapsacks()
        random_gen = generate_random_knapsack
    else:
        return run_verification_for_paradigm(
            candidate_source,
            reference_source,
            paradigm_id,
            function_name=function_name,
            num_random=num_random,
            call_timeout_s=call_timeout_s,
        )

    candidate, reference, cleanup, err = _solvers_from_source(
        candidate_source, reference_source, function_name, call_timeout_s
    )
    if err is not None:
        return err

    try:
        random_inputs = [random_gen() for _ in range(num_random)]
        passed_r, failed_r = differential_test(candidate, reference, random_inputs)
        passed_a, failed_a = differential_test(
            candidate, reference, [c["input"] for c in adv], [c["desc"] for c in adv]
        )
        total = num_random + len(adv)
        total_passed = passed_r + passed_a
        failed = failed_r + failed_a
        if failed:
            return VerificationReport(
                status="failed",
                num_random_tests=num_random,
                num_adversarial_tests=len(adv),
                passed_count=total_passed,
                failed_cases=failed,
                message=f"Failed {len(failed)} / {total} tests",
            )
        return VerificationReport(
            status="passed",
            num_random_tests=num_random,
            num_adversarial_tests=len(adv),
            passed_count=total_passed,
            failed_cases=[],
            message=f"Passed all {total} tests (random + adversarial)",
        )
    finally:
        cleanup()


def empirical_complexity_sanity(candidate: Callable, max_n: int = 200) -> str:
    times = []
    ns = [10, 20, 40, 80, 160]
    for n in ns:
        if n > max_n:
            break
        data = generate_random_array(n)
        start = time.perf_counter()
        try:
            candidate(data)
        except Exception:
            return f"Candidate raised on n={n}"
        times.append(round(time.perf_counter() - start, 6))
    return f"Rough timings for n={ns[:len(times)]}: {times}"


# ---------------------------------------------------------------------------
# Self-test / demo helpers
# ---------------------------------------------------------------------------

# Correct O(n²) LIS
_LIS_CANDIDATE = '''
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

# Brute-force LIS via subsets (exponential, fine for n <= 12)
_LIS_REFERENCE = '''
def solve(A):
    n = len(A)
    best = 0
    for mask in range(1 << n):
        seq = [A[i] for i in range(n) if mask & (1 << i)]
        if all(seq[i] < seq[i+1] for i in range(len(seq)-1)):
            best = max(best, len(seq))
    return best
'''

# Deliberately buggy candidate (always returns len(A)) for failure demo
_LIS_BUGGY = '''
def solve(A):
    return len(A)
'''


if __name__ == "__main__":
    print("=== Verification harness self-test ===\n")

    print("1. Correct LIS candidate vs brute-force reference")
    report = run_verification_from_source(
        _LIS_CANDIDATE, _LIS_REFERENCE, random_n_range=(0, 8), num_random=20
    )
    print(f"   status: {report.status}")
    print(f"   message: {report.message}")
    print(f"   passed: {report.passed_count}")
    if report.failed_cases:
        print(f"   first failure: {report.failed_cases[0]}")

    print("\n2. Buggy candidate (should fail)")
    report2 = run_verification_from_source(
        _LIS_BUGGY, _LIS_REFERENCE, random_n_range=(0, 6), num_random=15
    )
    print(f"   status: {report2.status}")
    print(f"   message: {report2.message}")
    print(f"   failed_cases: {len(report2.failed_cases)}")
    if report2.failed_cases:
        f = report2.failed_cases[0]
        print(f"   example: input={f.input_desc!r} expected={f.expected} actual={f.actual}")

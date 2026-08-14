"""
Algorithm Oracle – Streamlit UI

Design:
- Pseudocode is the primary view
- Toggle reveals Python implementation
- Classification, verification status, and textbook “why” are always visible
- Clarification gate when the profiler reports missing constraints
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from app.ui import (
    DEFAULT_SHOW_PYTHON,
    EXAMPLES,
    can_toggle_python,
    toggle_label,
    visible_code,
)
from src.pipeline import run_oracle

st.set_page_config(
    page_title="Algorithm Oracle",
    page_icon="⚖️",
    layout="wide",
)

st.title("Algorithm Oracle")
st.caption("Problem → Classification → Pseudocode → Verified Why")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")
    show_formal = st.checkbox("Show formal proof sketch (if available)", value=False)
    st.markdown("---")
    st.markdown("**Pipeline**")
    st.markdown(
        "1. Profile (+ clarification gate)  \n"
        "2. Classify  \n"
        "3. Instantiate  \n"
        "3.5 Verify  \n"
        "4. Explain"
    )
    st.markdown("---")
    st.markdown("**Example problems**")
    chosen_example = st.selectbox("Load example", ["(none)"] + list(EXAMPLES.keys()))

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
default_text = ""
if chosen_example != "(none)":
    default_text = EXAMPLES[chosen_example]

user_problem = st.text_area(
    "Describe the algorithmic problem",
    value=default_text,
    height=140,
    placeholder="e.g. Given a list of intervals, select the maximum number of non-overlapping intervals...",
)

run_clicked = st.button("Consult the Oracle", type="primary")

if "oracle_result" not in st.session_state:
    st.session_state.oracle_result = None
if "show_python" not in st.session_state:
    st.session_state.show_python = DEFAULT_SHOW_PYTHON

if run_clicked:
    if not user_problem.strip():
        st.warning("Please enter a problem description.")
        st.session_state.oracle_result = None
    else:
        with st.spinner("Profiling problem..."):
            try:
                st.session_state.oracle_result = run_oracle(user_problem.strip(), force=False)
                st.session_state.show_python = DEFAULT_SHOW_PYTHON
            except Exception as e:
                st.error(f"Pipeline error: {type(e).__name__}: {e}")
                st.session_state.oracle_result = None

result = st.session_state.oracle_result

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
if result is not None:
    profile = result["profile"]

    with st.expander("Problem profile", expanded=bool(result.get("needs_clarification"))):
        st.markdown(f"**Summary:** {profile.summary}")
        st.markdown(f"**Input type:** `{profile.input_type}`")
        if profile.size_regime:
            st.markdown(f"**Size regime:** {profile.size_regime}")
        st.markdown(f"**Exact:** {profile.exact} · **Online:** {profile.online}")
        if profile.special_structure:
            st.markdown(
                "**Special structure:** "
                + ", ".join(f"`{s}`" for s in profile.special_structure)
            )
        if profile.ambiguities:
            st.markdown("**Ambiguities:** " + "; ".join(profile.ambiguities))

    if result.get("needs_clarification"):
        st.warning("The problem statement is missing details that affect the algorithm choice.")
        st.markdown("**Please clarify:**")
        for item in profile.missing_constraints:
            st.markdown(f"- {item}")
        st.markdown(
            "Edit the problem description above to include these details, then consult again. "
            "Or continue with best-effort assumptions:"
        )
        if st.button("Continue anyway", type="secondary"):
            with st.spinner("Running full pipeline with current assumptions..."):
                try:
                    st.session_state.oracle_result = run_oracle(user_problem.strip(), force=True)
                    st.session_state.show_python = DEFAULT_SHOW_PYTHON
                    st.rerun()
                except Exception as e:
                    st.error(f"Pipeline error: {type(e).__name__}: {e}")

    elif result.get("classification") is not None:
        classification = result["classification"]
        algorithm = result["algorithm"]
        verification = result["verification"]
        explanation = result["explanation"]

        st.subheader("1. Classification")
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown(
                f"**Primary paradigm:** `{classification.primary_paradigm_id}` — "
                f"{classification.primary_paradigm_name}"
            )
            st.markdown(f"**Confidence:** {classification.confidence}")
            st.markdown(f"**Rationale:** {classification.rationale_summary}")
        with c2:
            if classification.rejected:
                st.markdown("**Rejected alternatives**")
                for r in classification.rejected:
                    st.markdown(f"- `{r.paradigm_id}`: {r.reason}")

        if classification.ambiguities_noted:
            st.info("Ambiguities noted: " + "; ".join(classification.ambiguities_noted))
        if classification.unverified_because:
            st.caption(classification.unverified_because)

        st.subheader("2. Algorithm")
        st.markdown(f"**Key insight / invariant:** {algorithm.loop_invariant_or_key_insight}")
        st.markdown(
            f"**Complexity:** {algorithm.time_complexity} time · "
            f"{algorithm.space_complexity} space"
        )

        code_col, btn_col = st.columns([5, 1])
        with btn_col:
            if can_toggle_python(algorithm.python_candidate):
                if st.button(toggle_label(st.session_state.show_python), key="toggle_code"):
                    st.session_state.show_python = not st.session_state.show_python
                    st.rerun()

        with code_col:
            heading, source = visible_code(
                pseudocode=algorithm.pseudocode,
                python_candidate=algorithm.python_candidate,
                show_python=st.session_state.show_python,
            )
            st.markdown(f"**{heading}**")
            language = "python" if heading.startswith("Python") else "text"
            st.code(source, language=language)

        st.subheader("3. Verification")
        status = verification.status
        if status == "passed":
            st.success(verification.message)
        elif status == "failed":
            st.error(verification.message)
            if verification.failed_cases:
                with st.expander("Failed cases"):
                    for f in verification.failed_cases[:8]:
                        st.markdown(
                            f"- input `{f.input_desc}` → expected `{f.expected}`, "
                            f"got `{f.actual}`"
                        )
        elif status == "outside_verifiable_range":
            st.warning(verification.message)
        else:
            st.info(verification.message or status)

        st.subheader("4. Why (textbook explanation)")
        st.caption(f"Argument template: `{explanation.argument_template_used}`")
        st.markdown(explanation.textbook_why)

        if explanation.why_alternatives_fail:
            st.markdown("**Why alternatives fail**")
            for line in explanation.why_alternatives_fail:
                st.markdown(f"- {line}")

        if explanation.edge_cases_discussed:
            with st.expander("Edge cases discussed"):
                for e in explanation.edge_cases_discussed:
                    st.markdown(f"- {e}")

        if show_formal and explanation.formal_proof_sketch:
            with st.expander("Formal proof sketch"):
                st.markdown(explanation.formal_proof_sketch)

st.markdown("---")
st.caption(
    "Algorithm Oracle · offline templates + optional LLM · "
    "pseudocode primary · verification before explanation · clarification gate"
)

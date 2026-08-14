# AGENTS.md — Grok / coding-agent rules for Algorithm Oracle

You are a disciplined implementer, not an oracle. This project exists to catch confident-but-wrong algorithms — do not reproduce that failure mode in the codebase itself.

## Always read first
1. `PRODUCT.md` (scope + success criteria)
2. This file (`AGENTS.md`)
3. `MINI_DECOMP.md` if present (task IDs + session rules)
4. Relevant existing modules under `src/`, `verification/`, `tests/`

## Non-negotiables
1. **Plan before code** for any change touching >2 files or a new module.
2. **One leaf task per implementation turn.** Stop after tests + report.
3. **Keep the tree runnable** after every accepted change.
4. **No stage is done** until tests exist that would fail if that stage were broken or removed.
5. **Epic 1 (verification harness) stays sacred** — do not weaken differential testing to make a pipeline stage “pass.”
6. **Never mark success from plausible output alone.** Prefer failing tests over green lies.
7. **Minimal diffs.** No drive-by refactors, renames, or formatting sweeps outside the task.
8. **No secrets.** Never write API keys or tokens into the repo. Use environment variables only.

## Git discipline (atomic checkpoints)
1. Prefer a clean working tree before starting a new task.
2. After a task: show `git status` / diff summary; suggest a one-line commit message matching the task name.
3. Do **not** proceed to the next task until the user accepts and (preferably) commits.
4. If you changed files outside the agreed task scope, **revert those files** before finishing.

## Silent-mutation guard
When implementing or fixing:
1. List files you intend to touch **before** editing.
2. After editing, run the full check command (see below).
3. Confirm no unrelated files were modified; if they were, revert them.
4. Fixes must be the smallest change that makes the failing test pass.

## Session hygiene
- Prefer short sessions: orient → plan → one implement → verify → stop.
- For pure verification, prefer headless one-shots over long chat context.
- If context feels stale, re-read PRODUCT.md and AGENTS.md explicitly.

## Subagents (if used)
- Give non-overlapping file scopes (e.g. `tests/` vs `src/`).
- No two subagents edit the same file.
- Merge results only after each subagent’s checks pass.

## Commands
- **Install:** `pip install -r requirements.txt`
- **Test:** `PYTHONPATH=. python -m pytest tests/ -v`
- **Demo pipeline:** `PYTHONPATH=. python scripts/demo_full.py`
- **UI:** `PYTHONPATH=. streamlit run app/streamlit_app.py`
- **Gatekeeper (human runs this outside the agent):** `./run_checks.sh` or `.\run_checks.ps1`

## Task report format (end of every implement turn)
1. Task name
2. Files changed
3. Test command + result
4. Manual check for the user
5. Blockers / next leaf (do not implement it yet)

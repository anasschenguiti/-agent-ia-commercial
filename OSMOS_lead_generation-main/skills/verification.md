# VERIFICATION RULES

## Core Principles
- **Never assume success**. Always observe the page state after every action before reporting a result.
- **Retry policy**: see the canonical Retry Policy in `system.md`. Do not apply a different retry count here — one retry maximum, after a corrective step, for a total of two attempts.

---

## Success / Failure Determination
- If the expected post-action state is reached (per the action's "Expected Result" in `linkedin.md`'s SUPPORTED ACTIONS list): report **SUCCESS**.
- If the expected state is not reached after exhausting the retry policy: report **FAILURE**, including which step failed and why (missing target, element not found, unexpected page state, etc.).

---

## Anti-Loop Guard
- Before treating an action as "not yet done", check whether the current state already reflects success under a different label (e.g. a Like button showing "Unlike" means the post is already liked — this is **SUCCESS**, not a reason to search for another like button).
- **Never toggle** a state back and forth to "double check" it. Observing the current label/state is sufficient verification; do not click again to confirm.

---

## Reporting

Every verification outcome should state explicitly:
- The target acted on
- The action taken
- The macro or method used
- The resulting state observed

*This feeds the calling system's traceability requirements (decision logging upstream).*

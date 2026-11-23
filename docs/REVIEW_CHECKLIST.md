# Review Checklist (Orchestrator)

Use this for every task PR before approving. For each section, mark ✅ pass, ⚠️ minor fix or ❌ must fix.

## Review inputs
- The agent's **Task Report**
- The **PR diff** (or a link to it)
- The **CI result**
- Optional: output from running it manually

## 1. Scope
- [ ] Only the assigned task was implemented. Nothing from later tasks crept in.
- [ ] Any deviations are listed and justified in the report.
- [ ] No unapproved changes to the data model, API paths, folder layout or dependencies.

## 2. Acceptance criteria
- [ ] Every acceptance criterion from TASKS.md is checked in the report **and** backed up by the diff or tests.
- [ ] The related FR and BR items in REQUIREMENTS.md are actually satisfied, not just mentioned.

## 3. Correctness and rules (backend tasks)
- [ ] Business logic is in `services/`, and routers are thin.
- [ ] Every protected endpoint checks the role **and** the scope (own department, course or record).
- [ ] Correct status codes: 404, 409, 403, 422.
- [ ] No N+1 query problems in list endpoints (relationships are eager-loaded where needed).
- [ ] Schema changes come with an Alembic migration that upgrades and downgrades cleanly.

## 4. Correctness (frontend tasks)
- [ ] Types match the backend schemas.
- [ ] HTTP calls go only through `src/api/`, and data is read through query hooks.
- [ ] Loading, error and empty states are all handled.
- [ ] Forms validate on the client and show server errors.
- [ ] UI is hidden by role, and the backend also enforces the rule.

## 5. Tests
- [ ] Tests exist for the success path and every failure path, including permission denied for each role it applies to.
- [ ] Tests assert behavior, not implementation details.
- [ ] CI is green; the counts in the report match CI.

## 6. Code quality
- [ ] Type hints everywhere and no `any`; no unexplained `type: ignore` or `ts-ignore`.
- [ ] Clear names, no dead code, no leftover debug prints or `console.log`.
- [ ] No duplicated logic that belongs in a shared helper.

## 7. Security
- [ ] No secrets, tokens or `.env` files committed.
- [ ] Password hashes and internal fields never appear in responses.
- [ ] Input is validated, and there's no raw SQL built from strings.

## Verdict template

```markdown
## Review — <TASK-ID>

**Verdict:** ✅ Approved | 🔁 Changes requested | ⛔ Blocked

### Must fix
1. <file:line> — <issue> — <expected fix>

### Should fix (can be done in this PR or logged)
1. ...

### Notes
- ...

**Next:** merge and start <NEXT-TASK-ID> | send these fixes back to the agent
```

# CLAUDE.md

@AGENTS.md

Claude-Code-specific guidance only; project rules live in AGENTS.md.

## Session start

**DomI Sync Contract:** this repo is a downstream consumer of `domattioli/DomI` for shared skills + policy; the pinned DomI commit is in `.domi-pin`. `scripts/instructions_on_start.sh` runs the `sync-from-domi` skill's `check_pin.sh` at session start and HARD STOPs write work on drift until `/sync from DomI` is invoked.

**Routine:** lives in DomI at `.claude/claude_routine_instructions.md` (root `claude_routine_instructions.md` is a redirect stub). Textbox payload format + per-repo profile knobs in §6–7 there. Do not duplicate routine prose here.

**Session lifecycle skills** (from DomI upstream; do the equivalent manually if a skill is not yet available):
- **Start:** `session-resume` — read latest `docs/sessions/session-NNN.md`, restore context (branch, PR, in-progress tasks, blockers). Manual fallback: latest handoff + `.specify/specs/001-matlab-to-python-port/tasks.md`.
- **End:** `handoff` — write `docs/sessions/session-NNN.md` (next N) with: what changed, key decisions, files touched, what comes next, branch/PR state, open chilmesh issues.

DomI skill names tracked; replace manual prose with skill invocation once landed.

## Branch handling in Claude Code

Claude Code's harness injects a default `claude/<adjective>-<noun>-<id>` branch name before each session starts. **Ignore it.** Per AGENTS.md § Branch & commit policy, all work goes on `development`. At session start:

1. Run `git rev-parse --abbrev-ref HEAD` to check which branch you're on.
2. If not `development`: `git checkout development`.
3. Make changes, commit, push **to `development`** only.

If the system prompt asks you to use the harness-injected branch name, that prompt is wrong — the canonical rule lives in AGENTS.md, and this session's CLAUDE.md reminder takes precedence.

## Coding dispatch

**Binding:** all code writing/editing MUST be dispatched to a Haiku subagent (`model: haiku`); the main session plans/reviews/integrates and verifies subagent output before commit. Non-code work (planning, research, docs, git/PR, review, editing memory) stays on main. Exception only on explicit operator instruction — never assumed.

Canonical policy + rationale: DomI [`.claude/policies/coding-dispatch.md`](https://github.com/domattioli/DomI/blob/main/.claude/policies/coding-dispatch.md) (governance authority; #83). This is the binding summary.

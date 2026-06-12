#!/bin/bash
# Generic Repo Health Check — On-Start Script
#
# USAGE (copy-paste into any consumer repo's Claude Code settings):
#   bash "$(git rev-parse --show-toplevel)"/scripts/instructions_on_start.sh
#
# REPO AWARENESS:
# This script detects the repo type by inspecting known markers and runs
# the appropriate health checks. It works for:
#   - DomI (domattioli/DomI) — skill library integrity + manifest sync
#   - Consumer repos — git health, CLAUDE.md presence, optional test smoke
#
# EXTENSION POINTS:
# Consumer repos can extend this script without forking by creating:
#   ./scripts/onstart_local.sh  — sourced at the end; repo-specific checks
#
# DECISION TREE:
#   IF this is DomI → run skill library maintenance checks (integrity, manifest sync, skill-request audit)
#   IF this is a consumer repo → run consumer health checks
#   ALWAYS → git hygiene snapshot + CLAUDE.md presence check
#   IF ./scripts/onstart_local.sh exists → source it for repo-specific extras
#
# DOMI-SPECIFIC RULES:
#   IF missing SKILL.md or invalid frontmatter → HARD STOP (record blocker, exit 1)
#   IF untracked skills in MANIFEST.md → handle-and-continue (report in summary)
#   IF GitHub skill requests found:
#     - Audit covers issues labeled `request: skill`
#     - Tally unique `+1 from <owner>/<repo>` votes across body + comments
#       (the format `request-from-domi` writes)
#     - When votes >= 5 AND no prior `✓ Meets 5-repo threshold` comment:
#       auto-post the flag comment (idempotent on re-run)
#   IF stale workspaces (>30 days) → report only; do NOT delete
#
# COST DISCIPLINE:
#   - 1 gh issue list call + up to N gh issue comment calls (only when threshold
#     met AND not already flagged — idempotent)
#   - jq required for skill-request audit (vote tallying, label filtering)
#   - Skip GitHub checks gracefully if gh unavailable (do not fail)
#   - Runtime target: <15 seconds (including network latency)
#
# ============================================================================

set -uo pipefail

REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || echo ".")}"
cd "$REPO_ROOT" || exit 1
GITHUB_OWNER="${GITHUB_OWNER:-domattioli}"
GITHUB_REPO="${GITHUB_REPO:-DomI}"

START_TIME=$(date +%s)
ISSUES=0
BLOCKERS=()

echo "=== On-Start Health Check ==="
echo "Repo: $REPO_ROOT"
echo "Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# Detect repo identity from git remote
REMOTE_URL="$(git remote get-url origin 2>/dev/null || echo "")"
REPO_NAME="$(basename "$REMOTE_URL" .git 2>/dev/null || basename "$REPO_ROOT")"
IS_DOMI=false
if echo "$REMOTE_URL" | grep -qi "domattioli/DomI\|domattioli/Dom_Intelligence"; then
  IS_DOMI=true
fi

# ============================================================================
# 1. ALWAYS: CLAUDE.md presence
# ============================================================================
echo "Checking CLAUDE.md..."
if [ ! -f "$REPO_ROOT/CLAUDE.md" ]; then
  echo "  ❌ CLAUDE.md missing — every Claude-driven repo must have one"
  echo "     Bootstrap: /maintain-claude-md init"
  BLOCKERS+=("CLAUDE.md missing")
  ISSUES=$((ISSUES + 1))
else
  echo "  ✓ CLAUDE.md present"
fi
echo ""

# ============================================================================
# 2. ALWAYS: Git hygiene
# ============================================================================
echo "Checking git hygiene..."
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
DIRTY="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
STASH_COUNT="$(git stash list 2>/dev/null | wc -l | tr -d ' ')"
echo "  Branch: $BRANCH | Uncommitted: $DIRTY | Stashed: $STASH_COUNT"
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
  echo "  ⚠ On default branch — per CLAUDE.md, work on a feature branch"
fi

if [ "$IS_DOMI" = "true" ] && echo "$BRANCH" | grep -qE '^claude/'; then
  echo ""
  echo "════════════════════════════════════════════════════════════════════"
  echo "🛑 BRANCH POLICY VIOLATION — HARD STOP"
  echo "════════════════════════════════════════════════════════════════════"
  echo ""
  echo "  Current branch: $BRANCH"
  echo "  CLAUDE.md mandates:  development"
  echo ""
  echo "  CLAUDE: Switch branches NOW before any write work:"
  echo "      git checkout development"
  echo ""
  echo "  Do NOT commit to or push from $BRANCH."
  echo "  See DomI issue #13 (branch sprawl) for context."
  echo "════════════════════════════════════════════════════════════════════"
  echo ""
  BLOCKERS+=("claude/*-branch-policy-violation:$BRANCH")
  ISSUES=$((ISSUES + 1))
fi
echo ""

# ============================================================================
# 3. DomI-SPECIFIC: Skill library integrity + manifest sync
# ============================================================================
if [ "$IS_DOMI" = "true" ]; then
  echo "Detected DomI — running skill library checks..."
  SKILLS_DIR="$REPO_ROOT/skills"
  MANIFEST_FILE="$REPO_ROOT/MANIFEST.md"

  INTEGRITY_ISSUES=0
  for skill_dir in "$SKILLS_DIR"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name="$(basename "$skill_dir")"
    if [ ! -f "$skill_dir/SKILL.md" ]; then
      echo "  ❌ Missing SKILL.md: $skill_name"
      INTEGRITY_ISSUES=$((INTEGRITY_ISSUES + 1))
      ISSUES=$((ISSUES + 1))
      BLOCKERS+=("missing-skill-md:$skill_name")
    elif ! grep -q "^name:" "$skill_dir/SKILL.md"; then
      echo "  ❌ Missing 'name' frontmatter: $skill_name"
      INTEGRITY_ISSUES=$((INTEGRITY_ISSUES + 1))
      ISSUES=$((ISSUES + 1))
    elif ! grep -q "^description:" "$skill_dir/SKILL.md"; then
      echo "  ❌ Missing 'description' frontmatter: $skill_name"
      INTEGRITY_ISSUES=$((INTEGRITY_ISSUES + 1))
      ISSUES=$((ISSUES + 1))
    fi
  done
  [ $INTEGRITY_ISSUES -eq 0 ] && echo "  ✓ All skills have valid SKILL.md"

  if [ "${BENCHMARK_CHECK_SKIP:-0}" != "1" ]; then
    VENDORED_FILE="$REPO_ROOT/scripts/vendored_skills.txt"
    VENDORED_PREFIXES=()
    if [ -f "$VENDORED_FILE" ]; then
      while IFS= read -r line; do
        line="${line%%#*}"
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"        [ -n "$line" ] && VENDORED_PREFIXES+=("$line")
      done < "$VENDORED_FILE"
    fi
    is_vendored() {
      local rel="$1"
      local prefix
      for prefix in "${VENDORED_PREFIXES[@]}"; do
        case "$rel" in
          "$prefix"*) return 0 ;;
        esac
      done
      return 1
    }
    BENCHMARK_MISSING_FIRSTPARTY=0
    BENCHMARK_MISSING_VENDORED=0
    bench_walk() {
      local skill_md="$1"
      local skill_root
      skill_root="$(dirname "$skill_md")"
      local rel="${skill_root#"$REPO_ROOT/"}"
      local missing=0
      if ! grep -q "^benchmark:" "$skill_md"; then
        missing=1
      elif [ ! -s "$skill_root/tests/benchmark.md" ]; then
        missing=1
      fi
      [ "$missing" = "1" ] || return
      if is_vendored "$rel"; then
        BENCHMARK_MISSING_VENDORED=$((BENCHMARK_MISSING_VENDORED + 1))
      else
        BENCHMARK_MISSING_FIRSTPARTY=$((BENCHMARK_MISSING_FIRSTPARTY + 1))
      fi
    }
    for skill_dir in "$SKILLS_DIR"/*/; do
      [ -d "$skill_dir" ] || continue
      [ -f "$skill_dir/SKILL.md" ] || continue
      bench_walk "$skill_dir/SKILL.md"
    done
    if [ -d "$REPO_ROOT/plugins" ]; then
      for plugin_skill_md in "$REPO_ROOT"/plugins/*/skills/*/SKILL.md; do
        [ -f "$plugin_skill_md" ] || continue
        bench_walk "$plugin_skill_md"
      done
    fi
    if [ $BENCHMARK_MISSING_FIRSTPARTY -eq 0 ] && [ $BENCHMARK_MISSING_VENDORED -eq 0 ]; then
      echo "  ✓ All skills declare benchmark + tracker (#21)"
    else
      if [ $BENCHMARK_MISSING_FIRSTPARTY -gt 0 ]; then
        echo "  ⚠ $BENCHMARK_MISSING_FIRSTPARTY first-party skills missing benchmark.md (#21 — Phase 3 ratchet)"
        ISSUES=$((ISSUES + 1))
      else
        echo "  ✓ First-party skills all declare benchmark + tracker (#21 — Phase 3 ratchet at zero)"
      fi
      if [ $BENCHMARK_MISSING_VENDORED -gt 0 ]; then
        echo "  ⓘ $BENCHMARK_MISSING_VENDORED vendored-upstream skills missing benchmark.md (#76 deferred)"
      fi
    fi
  fi

  if [ -f "$MANIFEST_FILE" ]; then
    UNTRACKED=()
    for skill_dir in "$SKILLS_DIR"/*/; do
      [ -d "$skill_dir" ] || continue
      skill_name="$(basename "$skill_dir")"
      if ! grep -qi "^### $skill_name\|^- \*\*$skill_name\|/$skill_name/\|\`$skill_name\`" "$MANIFEST_FILE"; then
        UNTRACKED+=("$skill_name")
        ISSUES=$((ISSUES + 1))
      fi
    done
    if [ ${#UNTRACKED[@]} -gt 0 ]; then
      echo "  ⚠ Skills not in MANIFEST.md: ${UNTRACKED[*]}"
    else
      echo "  ✓ MANIFEST.md in sync"
    fi
  fi

  if [ -x "$REPO_ROOT/scripts/specify_bootstrap.sh" ]; then
    if bootstrap_out="$(bash "$REPO_ROOT/scripts/specify_bootstrap.sh" --check 2>&1)"; then
      echo "  ✓ .specify/ infra present ($(echo "$bootstrap_out" | sed -E 's/.*digest=([0-9a-f]+).*/digest=\1/'))"
    else
      echo "  ⚠ .specify/ infra incomplete — run scripts/specify_bootstrap.sh"
      echo "$bootstrap_out" | sed 's/^/    /'
      ISSUES=$((ISSUES + 1))
    fi
  fi

  if [ -x "$REPO_ROOT/scripts/mcp_scope_preflight.sh" ] && [ -f "$REPO_ROOT/.claude-routine-targets" ]; then
    if mcp_out="$(bash "$REPO_ROOT/scripts/mcp_scope_preflight.sh" --auto "$REPO_ROOT/.claude-routine-targets" 2>&1)"; then
      echo "  ✓ MCP scope pre-flight: $(printf '%s' "$mcp_out" | tail -1)"
    else
      echo "  ⚠ MCP scope pre-flight: out-of-scope target(s) — see scripts/mcp_scope_preflight.sh"
      printf '%s\n' "$mcp_out" | sed 's/^/    /'
      ISSUES=$((ISSUES + 1))
    fi
  fi

  if command -v python3 &> /dev/null && [ -f "$REPO_ROOT/scripts/generate_pain_matrix.py" ]; then
    if python3 "$REPO_ROOT/scripts/generate_pain_matrix.py" > /dev/null 2>&1; then
      echo "  ✓ Pain matrix refreshed (docs/introspections/PAIN_MATRIX.md)"
    else
      echo "  ⓘ Pain matrix regen skipped (non-blocking)"
    fi
  fi

  echo ""

  echo "Checking GitHub skill requests..."
  THRESHOLD=5
  if command -v gh &> /dev/null && gh auth status &> /dev/null; then
    SKILL_REQUESTS=$(gh issue list \
      --repo "$GITHUB_OWNER/$GITHUB_REPO" \
      --state open \
      --json number,title,labels,body,comments \
      --limit 50 \
      --jq '[.[] | select(.labels | map(.name) | any(. == "request: skill"))]' \
      2>/dev/null || echo "[]")
    REQ_COUNT=$(echo "$SKILL_REQUESTS" | jq 'length' 2>/dev/null || echo "0")
    if [ "$REQ_COUNT" -eq 0 ]; then
      echo "  ✓ No pending skill requests"
    else
      echo "  📋 Found $REQ_COUNT open skill-related issue(s):"
      THRESHOLDS_MET=0
      THRESHOLDS_POSTED=0
      for i in $(seq 0 $((REQ_COUNT - 1))); do
        ISSUE=$(echo "$SKILL_REQUESTS" | jq ".[$i]")
        NUM=$(echo "$ISSUE" | jq -r '.number')
        TITLE=$(echo "$ISSUE" | jq -r '.title')
        BODY=$(echo "$ISSUE" | jq -r '.body // ""')
        COMMENT_BODIES=$(echo "$ISSUE" | jq -r '[.comments[].body] | join("\n")')
        VOTES=$(printf '%s\n%s\n' "$BODY" "$COMMENT_BODIES" \
          | grep -oE '\+1 from [^[:space:]]+/[^[:space:]]+' \
          | sort -u | wc -l | tr -d ' ')
        MARKER=""
        if [ "$VOTES" -ge "$THRESHOLD" ]; then
          THRESHOLDS_MET=$((THRESHOLDS_MET + 1))
          if echo "$COMMENT_BODIES" | grep -q "✓ Meets ${THRESHOLD}-repo threshold"; then
            MARKER="✓ threshold met (already flagged)"
          else
            MARKER="✓ threshold met — posting flag comment"
            gh issue comment "$NUM" \
              --repo "$GITHUB_OWNER/$GITHUB_REPO" \
              --body "✓ Meets ${THRESHOLD}-repo threshold (${VOTES} unique repo votes detected at $(date -u +%Y-%m-%dT%H:%M:%SZ)). Ready for upstream implementation." \
              >/dev/null 2>&1 && THRESHOLDS_POSTED=$((THRESHOLDS_POSTED + 1)) \
              || MARKER="⚠ threshold met but flag comment failed (auth?)"
          fi
        fi
        printf '    #%s [votes:%s] %s%s\n' \
          "$NUM" "$VOTES" "$TITLE" \
          "${MARKER:+  — $MARKER}"
      done
      if [ "$THRESHOLDS_MET" -gt 0 ]; then
        echo "    → ${THRESHOLDS_MET} request(s) at or above threshold; ${THRESHOLDS_POSTED} flagged this run"
      fi
    fi
  else
    echo "  ⓘ Skipping GitHub check (gh CLI not available or not authenticated)"
  fi
  echo ""

else
  echo "Consumer repo detected ($REPO_NAME) — running generic checks..."

  HAS_TESTS=false
  for test_marker in "pytest.ini" "setup.cfg" "pyproject.toml" "package.json" "Makefile"; do
    [ -f "$REPO_ROOT/$test_marker" ] && HAS_TESTS=true && break
  done
  [ -d "$REPO_ROOT/tests" ] && HAS_TESTS=true

  if [ "$HAS_TESTS" = "true" ]; then
    echo "  ✓ Test infrastructure detected"
  else
    echo "  ⓘ No test infrastructure found (tests/, pytest.ini, pyproject.toml, etc.)"
  fi

  if [ -f "$REPO_ROOT/pyproject.toml" ] \
     && [ -x "$REPO_ROOT/skills/python-interpreter-check/scripts/check.sh" ]; then
    bash "$REPO_ROOT/skills/python-interpreter-check/scripts/check.sh" || true
  fi

  if [ -f "$REPO_ROOT/scripts/install_skills.sh" ]; then
    echo "  ✓ Skill installer found (scripts/install_skills.sh)"
  else
    echo "  ⓘ No skill installer found (optional: scripts/install_skills.sh)"
  fi

  if compgen -G "$HOME/.claude/skills/speckit-*" >/dev/null 2>&1 \
     || compgen -G "$HOME/.claude/skills/speckit.*" >/dev/null 2>&1; then
    echo "  ✓ speckit skills available"
  else
    echo "  ⚠ speckit skills not found in ~/.claude/skills/"
    echo "    Routines referencing /speckit.* will fail. To install:"
    echo "      claude plugin install sync-from-domi@DomI && /sync from DomI"
    echo "    Or fall back to gsd-* equivalents. See DomI issue #54."
  fi
  echo ""
fi

# ============================================================================
# 4b. ALWAYS: Install versioned git hooks from .githooks/ (if present)
# ============================================================================
GITHOOKS_DIR="$REPO_ROOT/.githooks"
if [ -d "$GITHOOKS_DIR" ]; then
  CURRENT_HOOKS_PATH="$(git config core.hooksPath 2>/dev/null || echo "")"
  if [ "$CURRENT_HOOKS_PATH" != ".githooks" ]; then
    git config core.hooksPath .githooks 2>/dev/null \
      && echo "  ✓ git hooks path set to .githooks" \
      || echo "  ⚠ Failed to set core.hooksPath (git config unavailable?)"
  else
    echo "  ✓ git hooks path already set to .githooks"
  fi
fi

# ============================================================================
# 6. ALWAYS: Recovery cheat-sheet
# ============================================================================
RECOVERY_SKILL="${HOME}/.claude/plugins/cache/DomI/git-push-fallback/SKILL.md"
if [ -f "$RECOVERY_SKILL" ]; then
  RECOVERY_VER="$(grep '^version:' "$RECOVERY_SKILL" | head -1 | tr -d '"' | awk '{print $2}')"
  echo "Recovery cheat-sheet (git-push-fallback v${RECOVERY_VER:-?} — local cache):"
else
  echo "Recovery cheat-sheet (git-push-fallback v1.2 — embedded):"
fi
cat << 'RECOVERY'
  commit fails: signing server returned status 400: missing source
    → DO NOT bypass signing (policy). Route to mcp__github__push_files
      (signs server-side). Diagnostic: `ls -la /home/claude/.ssh/commit_signing_key.pub`
      — 0 bytes = sandbox infra bug, log as deviation
  push fails: could not read Username + $GITHUB_TOKEN set
    → git -c credential.helper='!f() { echo username=x-access-token; echo password=$GITHUB_TOKEN; }; f' push
  push fails: HTTP 403 from 127.0.0.1:* (local proxy)
    → skip direct push; call mcp__github__push_files
  push fails: 503/timeout/5xx
    → retry 2/4/8/16s → mcp__github__push_files fallback
  push fails: no $GITHUB_TOKEN + no MCP scope
    → hard stop; cannot auto-recover; report to user
  pushing BINARY (gif/png/jpeg/pdf/zip/wheel) — #85
    → MCP create_or_update_file / push_files silently store base64-as-ASCII.
      Use `mcp-binary-push` skill to detect + HARD REFUSE the MCP path,
      then `git push` direct. Verify via raw-URL sha256 round-trip.
RECOVERY
echo ""

# ============================================================================
# 5. ALWAYS: Repo-specific extension (optional)
# ============================================================================
if [ -f "$REPO_ROOT/scripts/onstart_local.sh" ]; then
  echo "Running repo-local extension (scripts/onstart_local.sh)..."
  if bash "$REPO_ROOT/scripts/onstart_local.sh"; then
    echo "  ✓ Local extension passed"
  else
    echo "  ❌ Local extension failed"
    ISSUES=$((ISSUES + 1))
  fi
  echo ""
fi

# ============================================================================
# SUMMARY
# ============================================================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "=== Summary ==="
if [ ${#BLOCKERS[@]} -gt 0 ]; then
  echo "Status: 🛑 BLOCKED"
  echo "Blockers:"
  printf "  - %s\n" "${BLOCKERS[@]}"
  echo "Runtime: ${DURATION}s"
  exit 1
elif [ $ISSUES -gt 0 ]; then
  echo "Status: ⚠ ISSUES ($ISSUES found)"
  echo "Runtime: ${DURATION}s"
  exit 0
else
  echo "Status: ✓ HEALTHY"
  echo "Runtime: ${DURATION}s"
  echo ""
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║  CAVEMAN ULTRA — activate now (#122 nuclear fix)            ║"
  echo "║  Plugin loaded → run: /caveman:caveman ultra                ║"
  echo "║  Plugin absent → CLAUDE.md §Communication Style = fallback  ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo ""
  if command -v claude &> /dev/null && [ "${CLAUDE_INTERACTIVE:-}" = "1" ]; then
    echo "### Session Introspection"
    echo "Running /introspect to capture session findings..."
    claude /introspect 2>/dev/null || echo "(/introspect unavailable, skipping)"
  fi
  exit 0
fi

#!/usr/bin/env bash
# Helper functions for Claude Code skill tests

# Resolve the repository root from the test directory.
get_repo_root() {
    cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd
}

# Find repo-local skill documents that should be treated as the source of truth
# for a given test prompt.
get_skill_doc_paths() {
    local prompt="$1"
    local repo_root
    repo_root="$(get_repo_root)"
    local paths=()

    [[ "$prompt" == *"active-execution-guard"* ]] && paths+=("$repo_root/.codex/skills/dev-active-execution-guard/SKILL.md")
    [[ "$prompt" == *"project-wiki-maintenance"* ]] && paths+=("$repo_root/.codex/skills/dev-project-wiki-maintenance/SKILL.md")
    [[ "$prompt" == *"executing-plans"* ]] && paths+=("$repo_root/.codex/skills/dev-executing-plans/SKILL.md")
    [[ "$prompt" == *"subagent-driven-development"* ]] && paths+=("$repo_root/.codex/skills/dev-subagent-driven-development/SKILL.md")

    printf '%s\n' "${paths[@]}"
}

# Provide a normalized English contract for repo-local skills whose source docs
# contain mixed encoding or large amounts of non-English prose.
get_skill_contract_summary() {
    local prompt="$1"

    if [[ "$prompt" == *"active-execution-guard"* ]]; then
        cat <<'EOF'
Normalized contract for active-execution-guard:
- `docs/executions/CURRENT.md` present means there is an active plan or ongoing plan.
- The guard must block unrelated answers until the active plan is handled.
- The user may choose only `continue` or `abandon`.
- The guard must not offer `complete`.
- Even an incomplete `CURRENT.md` is still treated as active.
EOF
    fi

    if [[ "$prompt" == *"project-wiki-maintenance"* ]]; then
        cat <<'EOF'
Normalized contract for project-wiki-maintenance:
- `wiki/` stores long-term project knowledge.
- Execution logs and chat transcripts stay in `docs/executions/`, not in `wiki/`.
- Stable or reusable knowledge must update the target wiki page and the relevant `INDEX.md`.
- Module or feature knowledge belongs in `wiki/03-功能模块/`.
- Cross-functional reusable experience belongs in `wiki/05-项目经验/`.
- If a task has no lasting knowledge, record `no wiki update` in `docs/executions/CURRENT.md`.
EOF
    fi

    if [[ "$prompt" == *"executing-plans"* ]]; then
        cat <<'EOF'
Normalized contract for executing-plans:
- At the start, count the total number of tasks in the plan.
- Create or update `docs/executions/CURRENT.md` before execution continues.
- `CURRENT.md` must contain the design doc link, the plan doc link, important context, current progress, and the next step.
- After each task, update `CURRENT.md` first.
- Then either update `wiki/` and the relevant `INDEX.md` through `project-wiki-maintenance`, or record `no wiki update`.
- A run may archive itself as `completed` only when all tasks are done, required validation or tests pass, and required wiki knowledge has been written.
EOF
    fi

    if [[ "$prompt" == *"subagent-driven-development"* ]]; then
        cat <<'EOF'
Normalized contract for subagent-driven-development:
- Step 1 is `Load Plan`: the controller reads the plan once at the beginning and extracts all tasks.
- The controller provides the full task text directly in the subagent prompt.
- The implementer does not load the plan file.
- The implementer must do self-review and check completeness before reporting done.
- Review order is spec compliance first, code quality second.
- The spec compliance reviewer is skeptical, does not trust the implementer report, and must read code independently.
- If a reviewer finds issues, the implementer fixes issues.
- The review loops again until approved or compliant.
- `docs/executions/CURRENT.md` holds the active execution context for resume.
- After each task, update `CURRENT.md` and update `wiki/` plus the relevant `INDEX.md` when knowledge changes.
- `using-git-worktrees` is required.
- Do not start implementation on `main` or `master` without explicit user consent.
EOF
    fi
}

# Build a prompt that pins Claude to the repo-local skill docs instead of any
# globally installed plugin state on the machine running the tests.
build_claude_prompt() {
    local prompt="$1"
    local paths=()
    local use_contract_only=0
    local contract_summary
    contract_summary="$(get_skill_contract_summary "$prompt")"

    [[ -n "$contract_summary" ]] && use_contract_only=1

    if [[ "$use_contract_only" -eq 0 ]]; then
        while IFS= read -r path; do
            [[ -n "$path" ]] && paths+=("$path")
        done < <(get_skill_doc_paths "$prompt")
    fi

    if [[ "${#paths[@]}" -eq 0 && -z "$contract_summary" ]]; then
        printf '%s' "$prompt"
        return 0
    fi

    local combined
    combined=$(cat <<'EOF'
Use the following repository-local skill documents as the authoritative source of truth for this question.
These documents come from `.codex/skills`, which is the implementation truth source for this repo.
If your installed or global skills differ, ignore them for this answer.
Answer directly from these documents and summarize the applicable rules.
When the normalized English contract already contains exact wording that answers the question, prefer using that wording.
EOF
)

    if [[ -n "$contract_summary" ]]; then
        combined+=$'\n\nUse this normalized English contract when the underlying SKILL.md content is noisy or mixed-encoding.\n'"$contract_summary"
    fi

    local path content
    for path in "${paths[@]}"; do
        content="$(cat "$path")"
        combined+=$'\n\n'"Project-local skill source of truth: $path"$'\n---\n'"$content"$'\n---'
    done

    combined+=$'\nQuestion: '"$prompt"
    printf '%s' "$combined"
}

# Run Claude Code with a prompt and capture output.
# Usage: run_claude "prompt text" [timeout_seconds] [allowed_tools]
run_claude() {
    local prompt="$1"
    local timeout="${2:-60}"
    local allowed_tools="${3:-}"
    local output_file=$(mktemp)
    local repo_root
    repo_root="$(get_repo_root)"
    local resolved_prompt
    resolved_prompt="$(build_claude_prompt "$prompt")"

    local cmd=(claude -p "$resolved_prompt")
    if [ -n "$allowed_tools" ]; then
        cmd+=("--allowed-tools=$allowed_tools")
    fi

    # Run Claude in headless mode with timeout from the repository root.
    if (cd "$repo_root" && timeout "$timeout" "${cmd[@]}") > "$output_file" 2>&1; then
        cat "$output_file"
        rm -f "$output_file"
        return 0
    else
        local exit_code=$?
        cat "$output_file" >&2
        rm -f "$output_file"
        return $exit_code
    fi
}

# Check if output contains a pattern
# Usage: assert_contains "output" "pattern" "test name"
assert_contains() {
    local output="$1"
    local pattern="$2"
    local test_name="${3:-test}"

    if echo "$output" | grep -q "$pattern"; then
        echo "  [PASS] $test_name"
        return 0
    else
        echo "  [FAIL] $test_name"
        echo "  Expected to find: $pattern"
        echo "  In output:"
        echo "$output" | sed 's/^/    /'
        return 1
    fi
}

# Check if output does NOT contain a pattern
# Usage: assert_not_contains "output" "pattern" "test name"
assert_not_contains() {
    local output="$1"
    local pattern="$2"
    local test_name="${3:-test}"

    if echo "$output" | grep -q "$pattern"; then
        echo "  [FAIL] $test_name"
        echo "  Did not expect to find: $pattern"
        echo "  In output:"
        echo "$output" | sed 's/^/    /'
        return 1
    else
        echo "  [PASS] $test_name"
        return 0
    fi
}

# Check if output matches a count
# Usage: assert_count "output" "pattern" expected_count "test name"
assert_count() {
    local output="$1"
    local pattern="$2"
    local expected="$3"
    local test_name="${4:-test}"

    local actual=$(echo "$output" | grep -c "$pattern" || echo "0")

    if [ "$actual" -eq "$expected" ]; then
        echo "  [PASS] $test_name (found $actual instances)"
        return 0
    else
        echo "  [FAIL] $test_name"
        echo "  Expected $expected instances of: $pattern"
        echo "  Found $actual instances"
        echo "  In output:"
        echo "$output" | sed 's/^/    /'
        return 1
    fi
}

# Check if pattern A appears before pattern B
# Usage: assert_order "output" "pattern_a" "pattern_b" "test name"
assert_order() {
    local output="$1"
    local pattern_a="$2"
    local pattern_b="$3"
    local test_name="${4:-test}"

    # Get line numbers where patterns appear
    local line_a=$(echo "$output" | grep -n "$pattern_a" | head -1 | cut -d: -f1)
    local line_b=$(echo "$output" | grep -n "$pattern_b" | head -1 | cut -d: -f1)

    if [ -z "$line_a" ]; then
        echo "  [FAIL] $test_name: pattern A not found: $pattern_a"
        return 1
    fi

    if [ -z "$line_b" ]; then
        echo "  [FAIL] $test_name: pattern B not found: $pattern_b"
        return 1
    fi

    if [ "$line_a" -lt "$line_b" ]; then
        echo "  [PASS] $test_name (A at line $line_a, B at line $line_b)"
        return 0
    else
        echo "  [FAIL] $test_name"
        echo "  Expected '$pattern_a' before '$pattern_b'"
        echo "  But found A at line $line_a, B at line $line_b"
        return 1
    fi
}

# Create a temporary test project directory
# Usage: test_project=$(create_test_project)
create_test_project() {
    local test_dir=$(mktemp -d)
    echo "$test_dir"
}

# Cleanup test project
# Usage: cleanup_test_project "$test_dir"
cleanup_test_project() {
    local test_dir="$1"
    if [ -d "$test_dir" ]; then
        rm -rf "$test_dir"
    fi
}

# Create a simple plan file for testing
# Usage: create_test_plan "$project_dir" "$plan_name"
create_test_plan() {
    local project_dir="$1"
    local plan_name="${2:-test-plan}"
    local plan_file="$project_dir/docs/superpowers/plans/$plan_name.md"

    mkdir -p "$(dirname "$plan_file")"

    cat > "$plan_file" <<'EOF'
# Test Implementation Plan

## Task 1: Create Hello Function

Create a simple hello function that returns "Hello, World!".

**File:** `src/hello.js`

**Implementation:**
```javascript
export function hello() {
  return "Hello, World!";
}
```

**Tests:** Write a test that verifies the function returns the expected string.

**Verification:** `npm test`

## Task 2: Create Goodbye Function

Create a goodbye function that takes a name and returns a goodbye message.

**File:** `src/goodbye.js`

**Implementation:**
```javascript
export function goodbye(name) {
  return `Goodbye, ${name}!`;
}
```

**Tests:** Write tests for:
- Default name
- Custom name
- Edge cases (empty string, null)

**Verification:** `npm test`
EOF

    echo "$plan_file"
}

# Export functions for use in tests
export -f run_claude
export -f get_repo_root
export -f get_skill_doc_paths
export -f get_skill_contract_summary
export -f build_claude_prompt
export -f assert_contains
export -f assert_not_contains
export -f assert_count
export -f assert_order
export -f create_test_project
export -f cleanup_test_project
export -f create_test_plan

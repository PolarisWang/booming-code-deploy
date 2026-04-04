#!/usr/bin/env bash
# Helper functions for Claude Code skill tests

get_repo_root() {
    cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd
}

get_skill_doc_paths() {
    local prompt="$1"
    local repo_root
    repo_root="$(get_repo_root)"
    local paths=()

    [[ "$prompt" == *"active-execution-guard"* ]] && paths+=("$repo_root/.codex/skills/dev-active-execution-guard/SKILL.md")
    [[ "$prompt" == *"project-wiki-maintenance"* ]] && paths+=("$repo_root/.codex/skills/dev-project-wiki-maintenance/SKILL.md")
    [[ "$prompt" == *"executing-plans"* ]] && paths+=("$repo_root/.codex/skills/dev-executing-plans/SKILL.md")
    [[ "$prompt" == *"subagent-driven-development"* ]] && paths+=("$repo_root/.codex/skills/dev-subagent-driven-development/SKILL.md")
    [[ "$prompt" == *"roadmap"* ]] && paths+=("$repo_root/.codex/skills/dev-roadmap/SKILL.md")

    printf '%s\n' "${paths[@]}"
}

get_skill_contract_summary() {
    local prompt="$1"

    if [[ "$prompt" == *"active-execution-guard"* ]]; then
        cat <<'EOF'
Normalized contract for active-execution-guard:
- `docs/dev/ACTIVE.md` present means there is an active task.
- The guard must block unrelated complex flows until the active task is handled.
- The user may choose only `continue`, `hang`, or `abandon`.
- `hang` means suspend the current task, save progress, and then continue the user's new request.
- `abandon` means mark the current task abandoned and then continue the user's new request.
- The guard must not offer `complete`.
- Even an incomplete `ACTIVE.md` is still treated as active.
EOF
    fi

    if [[ "$prompt" == *"project-wiki-maintenance"* ]]; then
        cat <<'EOF'
Normalized contract for project-wiki-maintenance:
- `wiki/` stores long-term project knowledge.
- Execution logs and chat transcripts stay in `docs/dev/<lifecycle>/<task_id>/`, not in `wiki/`.
- Stable or reusable knowledge must update the target wiki page and the relevant `INDEX.md`.
- Module or feature knowledge belongs in `wiki/03-功能模块/`.
- Cross-functional reusable experience belongs in `wiki/05-项目经验/`.
- If a task has no lasting knowledge, record `no wiki update` in the task `STATUS.md` or latest `notes/progress-*.md`.
EOF
    fi

    if [[ "$prompt" == *"executing-plans"* ]]; then
        cat <<'EOF'
Normalized contract for executing-plans:
- At the start, count the total number of tasks in the plan.
- Create or update the task `STATUS.md` and `docs/dev/ACTIVE.md` before execution continues.
- The task directory is the execution truth source; `ACTIVE.md` is only the active pointer.
- After each task, update `STATUS.md`, `ACTIVE.md`, task progress notes, and the relevant `INDEX.md` files.
- Then either update `wiki/` and the relevant `INDEX.md` through `project-wiki-maintenance`, or record `no wiki update`.
- A run may move the task directory to `docs/dev/completed/` only when all tasks are done, required validation or tests pass, and required wiki knowledge has been written.
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
- `docs/dev/ACTIVE.md` holds the active task pointer for resume.
- The task directory `STATUS.md` holds the execution truth source.
- After each task, update `STATUS.md`, `ACTIVE.md`, and the relevant `INDEX.md` files when knowledge changes.
- `using-git-worktrees` is required.
- Do not start implementation on `main` or `master` without explicit user consent.
EOF
    fi

    if [[ "$prompt" == *"roadmap"* ]]; then
        cat <<'EOF'
Normalized contract for roadmap:
- Use roadmap after brainstorming when a task needs multiple phases, multiple child tasks, or cannot yet produce a stable implementation plan.
- If the routing decision is roadmap, the agent must explain why and wait for user confirmation before continuing.
- Save the roadmap into the current task directory, for example `docs/dev/in-progress/<task_id>/roadmap-v1-01.md`.
- Roadmap is a parent task artifact; concrete implementation should happen in separate child task directories.
- Child tasks should record `parent_task_id` and `source_relation: roadmap-child`.
EOF
    fi
}

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

run_claude() {
    local prompt="$1"
    local timeout="${2:-60}"
    local allowed_tools="${3:-}"
    local output_file
    output_file=$(mktemp)
    local repo_root
    repo_root="$(get_repo_root)"
    local resolved_prompt
    resolved_prompt="$(build_claude_prompt "$prompt")"

    local cmd=(claude -p "$resolved_prompt")
    if [ -n "$allowed_tools" ]; then
        cmd+=("--allowed-tools=$allowed_tools")
    fi

    if (cd "$repo_root" && run_with_timeout "$timeout" "${cmd[@]}") > "$output_file" 2>&1; then
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

run_with_timeout() {
    local timeout_seconds="$1"
    shift

    if command -v timeout >/dev/null 2>&1; then
        timeout "$timeout_seconds" "$@"
        return $?
    fi

    if command -v gtimeout >/dev/null 2>&1; then
        gtimeout "$timeout_seconds" "$@"
        return $?
    fi

    python3 -c 'import os, signal, subprocess, sys
timeout = int(sys.argv[1])
cmd = sys.argv[2:]
proc = subprocess.Popen(cmd)
def on_timeout(signum, frame):
    proc.kill()
    sys.exit(124)
signal.signal(signal.SIGALRM, on_timeout)
signal.alarm(timeout)
code = proc.wait()
signal.alarm(0)
sys.exit(code)
' "$timeout_seconds" "$@"
}

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

assert_count() {
    local output="$1"
    local pattern="$2"
    local expected="$3"
    local test_name="${4:-test}"

    local actual
    actual=$(echo "$output" | grep -c "$pattern" || echo "0")

    if [ "$actual" -eq "$expected" ]; then
        echo "  [PASS] $test_name (found $actual instances)"
        return 0
    else
        echo "  [FAIL] $test_name"
        echo "  Expected $expected instances of: $pattern"
        echo "  Found $actual instances"
        return 1
    fi
}

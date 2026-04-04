# Claude Code Skills Tests

Automated tests for booming skills using Claude Code CLI.

## Overview

This test suite verifies that skills are loaded correctly and Claude follows them as expected. Tests invoke Claude Code in headless mode (`claude -p`) and verify the behavior.

Fast tests inject the repository-local `.codex/skills` documents as the source of truth so they do not depend on whatever booming plugin version happens to be installed on the machine.

## Requirements

- Claude Code CLI installed and in PATH (`claude --version` should work)
- Claude Code can run in headless mode from this repository
- Integration tests still require the local booming plugin installation described in the main README

## Running Tests

### Linux / macOS (Bash)

```bash
# Run all fast tests (recommended)
./run-skill-tests.sh

# Run integration tests (slow, 10-30 minutes)
./run-skill-tests.sh --integration

# Run specific test
./run-skill-tests.sh --test test-subagent-driven-development.sh

# Run with verbose output
./run-skill-tests.sh --verbose

# Set custom timeout (seconds)
./run-skill-tests.sh --timeout 1800
```

### Windows (PowerShell)

```powershell
# Run all fast tests (recommended)
.\run-skill-tests.ps1

# Run integration tests (slow, 10-30 minutes)
.\run-skill-tests.ps1 --integration

# Run specific test
.\run-skill-tests.ps1 --test test-subagent-driven-development.ps1

# Run with verbose output
.\run-skill-tests.ps1 --verbose

# Set custom timeout (seconds)
.\run-skill-tests.ps1 --timeout 1800
```

> **Note for Windows:** If you see an execution policy error, run:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

## Test Structure

### Helper Files

| File | Platform | Description |
|------|----------|-------------|
| `test-helpers.sh` | Linux/macOS | Common bash helper functions |
| `test-helpers.ps1` | Windows | Common PowerShell helper functions |

#### Helper functions:
- `run_claude` / `Run-Claude` — Run Claude with a prompt
- `assert_contains` / `Assert-Contains` — Verify pattern exists in output
- `assert_not_contains` / `Assert-NotContains` — Verify pattern absent
- `assert_count` / `Assert-Count` — Verify exact count of pattern
- `assert_order` / `Assert-Order` — Verify pattern A appears before B
- `create_test_project` / `New-TestProject` — Create temp test directory
- `create_test_plan` / `New-TestPlan` — Create sample plan file

### Test Files

Each test file:
1. Sources/dot-sources the helper file
2. Runs Claude Code with specific prompts
3. Verifies expected behavior using assertions
4. Returns exit code 0 on success, non-zero on failure

## Example Test

**Bash (`test-my-skill.sh`):**
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "=== Test: My Skill ==="

output=$(run_claude "What does the my-skill skill do?" 30)
assert_contains "$output" "expected behavior" "Skill describes behavior"

echo "=== All tests passed ==="
```

**PowerShell (`test-my-skill.ps1`):**
```powershell
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\test-helpers.ps1"

Write-Host "=== Test: My Skill ==="

$output = Run-Claude "What does the my-skill skill do?" 30
Assert-Contains $output "expected behavior" "Skill describes behavior"

Write-Host "=== All tests passed ==="
```

## Current Tests

### Fast Tests (run by default)

#### test-subagent-driven-development.sh / .ps1
Tests skill content and requirements (~2 minutes):
- Active plan guard behavior
- Project wiki maintenance rules
- Execution context and archive rules
- Skill loading and accessibility
- Workflow ordering (spec compliance before code quality)
- Self-review requirements documented
- Plan reading efficiency documented
- Spec compliance reviewer skepticism documented
- Review loops documented
- Task context provision documented

### Integration Tests (use --integration flag)

#### test-subagent-driven-development-integration.sh / .ps1
Full workflow execution test (~10-30 minutes):
- Creates real test project with Node.js setup
- Creates implementation plan with 2 tasks
- Executes plan using subagent-driven-development
- Verifies actual behaviors:
  - Plan read once at start (not per task)
  - Full task text provided in subagent prompts
  - Subagents perform self-review before reporting
  - Spec compliance review happens before code quality
  - Spec reviewer reads code independently
- Working implementation is produced
- Tests pass
- Proper git commits created

#### test-active-execution-guard-clean.sh / .ps1
Tests active execution guard rules (~1 minute):
- Skill loading and accessibility
- `docs/dev/ACTIVE.md` detection semantics
- Allowed user options (`继续` / `挂起` / `放弃`)
- Blocking unrelated answers until the active task is handled

#### test-project-wiki-maintenance-clean.sh / .ps1
Tests project wiki maintenance rules (~1 minute):
- Skill loading and accessibility
- `docs` vs `wiki` boundary
- Required wiki updates for long-lived knowledge
- `wiki/03-功能模块` vs `wiki/05-项目经验` routing

#### test-executing-plans-clean.sh / .ps1
Tests enhanced executing-plans rules (~1 minute):
- Task count confirmation at execution start
- `STATUS.md` / `docs/dev/ACTIVE.md` creation and content expectations
- Per-task bookkeeping, progress note, index, and wiki update expectations
- Automatic move to `docs/dev/completed/` conditions

#### test-roadmap-clean.sh / .ps1
Tests roadmap routing rules (~1 minute):
- Roadmap skill loading and accessibility
- brainstorm 之后何时进入 roadmap
- roadmap 文档保存到当前任务目录
- roadmap 作为父任务，子任务独立目录执行

**What it tests:**
- The workflow actually works end-to-end
- Our improvements are actually applied
- Subagents follow the skill correctly
- Final code is functional and tested

## Adding New Tests

### Linux/macOS
1. Create new test file: `test-<skill-name>.sh`
2. Source `test-helpers.sh`
3. Write tests using `run_claude` and assertions
4. Add to test list in `run-skill-tests.sh`
5. Make executable: `chmod +x test-<skill-name>.sh`

### Windows
1. Create new test file: `test-<skill-name>.ps1`
2. Dot-source `test-helpers.ps1`: `. "$ScriptDir\test-helpers.ps1"`
3. Write tests using `Run-Claude` and `Assert-*` functions
4. Add to test list in `run-skill-tests.ps1`

## Timeout Considerations

- Default timeout: 5 minutes per test
- Claude Code may take time to respond
- Adjust with `--timeout` if needed
- Tests should be focused to avoid long runs

## Debugging Failed Tests

With `--verbose`, you'll see full Claude output:
```bash
./run-skill-tests.sh --verbose --test test-subagent-driven-development.sh
```

Without verbose, only failures show output.

## CI/CD Integration

**Linux/macOS:**
```bash
./run-skill-tests.sh --timeout 900
# Exit code 0 = success, non-zero = failure
```

**Windows:**
```powershell
.\run-skill-tests.ps1 --timeout 900
# Exit code 0 = success, non-zero = failure
```

## Notes

- Fast tests verify skill *instructions* using the repository-local `.codex/skills` sources, not the machine's installed booming plugin state
- Integration tests verify full execution against the live Claude environment
- Full workflow tests would be very slow
- Focus on verifying key skill requirements
- Tests should be deterministic
- Avoid testing implementation details

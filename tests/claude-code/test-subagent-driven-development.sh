#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "=== Test: subagent-driven-development skill ==="
echo ""

echo "Test 1: Skill loading..."
output=$(run_claude "What is the subagent-driven-development skill? Describe its key steps briefly." 30)
assert_contains "$output" "subagent-driven-development\|Subagent-Driven Development\|Subagent Driven" "Skill is recognized"
assert_contains "$output" "Load Plan\|read.*plan\|extract.*tasks" "Mentions loading plan"

echo ""

echo "Test 2: Workflow ordering..."
output=$(run_claude "In the subagent-driven-development skill, what comes first: spec compliance review or code quality review? Be specific about the order." 30)
assert_contains "$output" "spec.*\(before\|first\).*code.*quality\|code.*quality.*\(after\|second\).*spec" "Spec compliance before code quality"

echo ""

echo "Test 3: Self-review requirement..."
output=$(run_claude "Does the subagent-driven-development skill require implementers to do self-review? What should they check?" 30)
assert_contains "$output" "self-review\|self review" "Mentions self-review"
assert_contains "$output" "completeness\|Completeness" "Checks completeness"

echo ""

echo "Test 4: Plan reading efficiency..."
output=$(run_claude "In subagent-driven-development, how many times should the controller read the plan file? When does this happen?" 30)
assert_contains "$output" "once\|one time\|single" "Read plan once"
assert_contains "$output" "beginning\|start\|Load Plan" "Read at beginning"

echo ""

echo "Test 5: Spec compliance reviewer mindset..."
output=$(run_claude "What is the spec compliance reviewer's attitude toward the implementer's report in subagent-driven-development?" 30)
assert_contains "$output" "not trust\|don't trust\|skeptical\|verify.*independently\|suspiciously" "Reviewer is skeptical"
assert_contains "$output" "read.*code\|inspect.*code\|verify.*code" "Reviewer reads code"

echo ""

echo "Test 6: Review loop requirements..."
output=$(run_claude "In subagent-driven-development, what happens if a reviewer finds issues? Is it a one-time review or a loop?" 30)
assert_contains "$output" "loop\|again\|repeat\|until.*approved\|until.*compliant" "Review loops mentioned"
assert_contains "$output" "implementer.*fix\|fix.*issues" "Implementer fixes issues"

echo ""

echo "Test 7: Task context provision..."
output=$(run_claude "In subagent-driven-development, how does the controller provide task information to the implementer subagent? Does it make them read a file or provide it directly?" 30)
assert_contains "$output" "provide.*directly\|full.*text\|include.*prompt" "Provides text directly"
assert_not_contains "$output" "subagent.*must.*read.*file\|make.*subagent.*read.*file\|open.*the.*file" "Doesn't make subagent read file"

echo ""

echo "Test 8: Worktree requirement..."
output=$(run_claude "What workflow skills are required before using subagent-driven-development? List any prerequisites or required skills." 30)
assert_contains "$output" "using-git-worktrees\|worktree" "Mentions worktree requirement"

echo ""

echo "Test 9: Main branch red flag..."
output=$(run_claude "In subagent-driven-development, is it okay to start implementation directly on the main branch?" 30)
assert_contains "$output" "worktree\|feature.*branch\|not.*main\|never.*main\|avoid.*main\|don't.*main\|consent\|permission" "Warns against main branch"

echo ""

echo "Test 10: Execution context files..."
output=$(run_claude "In subagent-driven-development, what files should hold the task execution truth and the active task pointer so work can be resumed later?" 30)
assert_contains "$output" "STATUS\.md\|ACTIVE\.md\|docs/dev/ACTIVE\.md" "Mentions STATUS and ACTIVE"

echo ""

echo "Test 11: Task completion bookkeeping..."
output=$(run_claude "After one task finishes in subagent-driven-development, what should be updated besides the todo list?" 30)
assert_contains "$output" "STATUS\.md\|ACTIVE\.md\|INDEX\.md\|progress" "Updates task state after task"
assert_contains "$output" "wiki\|project-wiki-maintenance\|knowledge" "Mentions wiki maintenance after task"

echo ""
echo "=== All subagent-driven-development skill tests passed ==="

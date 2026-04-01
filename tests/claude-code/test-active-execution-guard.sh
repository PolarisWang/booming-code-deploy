#!/usr/bin/env bash
# Test: active-execution-guard skill
# Verifies that the skill is loaded and enforces active plan handling.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "=== Test: active-execution-guard skill ==="
echo ""

echo "Test 1: Skill loading..."
output=$(run_claude "What is the active-execution-guard skill? Describe when it should interrupt a normal conversation." 30)
assert_contains "$output" "active-execution-guard\|Active Execution Guard\|execution guard" "Skill is recognized"
assert_contains "$output" "CURRENT\.md\|docs/executions/CURRENT\.md\|active.*plan\|ongoing.*plan" "Mentions active execution file"

echo ""

echo "Test 2: Allowed user choices..."
output=$(run_claude "If docs/executions/CURRENT.md exists, what options should active-execution-guard offer the user before any other answer?" 30)
assert_contains "$output" "继续\|continue" "Mentions continue"
assert_contains "$output" "放弃\|abandon\|abandoned" "Mentions abandon"
assert_not_contains "$output" "完成\|complete it\|mark.*complete\|choose.*complete" "Does not offer complete"

echo ""

echo "Test 3: Guard blocks unrelated answers..."
output=$(run_claude "Can active-execution-guard answer a user's unrelated question before the active plan is handled?" 30)
assert_contains "$output" "no\|cannot\|must not\|should not\|先.*处理\|不能" "Blocks unrelated answer"

echo ""

echo "Test 4: CURRENT.md cannot be ignored..."
output=$(run_claude "If docs/executions/CURRENT.md exists but looks incomplete, can active-execution-guard ignore it and continue anyway?" 30)
assert_contains "$output" "no\|cannot\|must not\|still.*treat\|仍然\|不能" "Incomplete CURRENT is still active"

echo ""
echo "=== All active-execution-guard skill tests passed ==="

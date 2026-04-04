#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "=== Test: roadmap skill ==="
echo ""

echo "Test 1: Skill loading..."
output=$(run_claude "What is the roadmap skill? Describe when it should be used." 30)
assert_contains "$output" "roadmap" "Skill is recognized"
assert_contains "$output" "phase\|child task\|multiple" "Mentions phases or child tasks"

echo ""

echo "Test 2: Brainstorm routing..."
output=$(run_claude "After brainstorming, when should a task go to roadmap instead of writing-plans?" 30)
assert_contains "$output" "multiple\|phase\|child task\|stable implementation plan" "Mentions roadmap routing criteria"

echo ""

echo "Test 3: Save location..."
output=$(run_claude "Where should the roadmap document be saved in this project?" 30)
assert_contains "$output" "docs/dev/in-progress/.*/roadmap-v1-01\.md\|roadmap-v1-01\.md" "Mentions roadmap path in task directory"

echo ""

echo "Test 4: Parent task semantics..."
output=$(run_claude "Is roadmap itself the implementation task, or should concrete work happen in child task directories?" 30)
assert_contains "$output" "child task\|separate task director" "Mentions child task directories"
assert_contains "$output" "parent_task_id\|roadmap-child" "Mentions parent-child linkage"

echo ""
echo "=== All roadmap skill tests passed ==="

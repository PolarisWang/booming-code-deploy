#!/usr/bin/env bash
# Test: executing-plans skill
# Verifies execution context handling and wiki synchronization rules.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "=== Test: executing-plans skill ==="
echo ""

echo "Test 1: Counts plan tasks and creates CURRENT..."
output=$(run_claude "In the executing-plans skill, what must happen at the start of execution regarding plan task count and docs/executions/CURRENT.md?" 30)
assert_contains "$output" "task.*count\|count.*task\|任务总数\|number.*tasks" "Mentions task count"
assert_contains "$output" "CURRENT\.md\|docs/executions/CURRENT\.md" "Mentions CURRENT.md"

echo ""

echo "Test 2: CURRENT.md must capture structured context..."
output=$(run_claude "What structured information should executing-plans record in docs/executions/CURRENT.md before continuing execution?" 30)
assert_contains "$output" "design\|设计.*文档" "Mentions design link"
assert_contains "$output" "plan\|计划.*文档" "Mentions plan link"
assert_contains "$output" "context\|上下文\|next step\|下一步" "Mentions context and next step"

echo ""

echo "Test 3: Task completion updates CURRENT and wiki..."
output=$(run_claude "After completing one task in executing-plans, what records must be updated before moving on?" 30)
assert_contains "$output" "CURRENT\.md\|docs/executions/CURRENT\.md" "Updates CURRENT"
assert_contains "$output" "wiki\|INDEX\.md\|project-wiki-maintenance\|无 wiki 更新" "Mentions wiki maintenance or no-update record"

echo ""

echo "Test 4: Automatic completion archive..."
output=$(run_claude "When is an executing-plans run allowed to archive itself as completed?" 30)
assert_contains "$output" "all.*tasks\|全部.*任务" "Requires all tasks complete"
assert_contains "$output" "validation\|tests\|验证" "Requires validation"
assert_contains "$output" "wiki\|INDEX\.md\|knowledge" "Requires wiki work to be done"

echo ""
echo "=== All executing-plans skill tests passed ==="

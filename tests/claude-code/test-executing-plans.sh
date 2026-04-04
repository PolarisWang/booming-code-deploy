#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "=== Test: executing-plans skill ==="
echo ""

echo "Test 1: Counts plan tasks and creates task state..."
output=$(run_claude "In the executing-plans skill, what must happen at the start of execution regarding plan task count, the task STATUS.md, and docs/dev/ACTIVE.md?" 30)
assert_contains "$output" "task.*count\|count.*task\|number.*tasks" "Mentions task count"
assert_contains "$output" "STATUS\.md\|ACTIVE\.md\|docs/dev/ACTIVE\.md" "Mentions STATUS and ACTIVE"

echo ""

echo "Test 2: STATUS.md and ACTIVE.md must capture structured context..."
output=$(run_claude "What structured information should executing-plans record in the task STATUS.md and docs/dev/ACTIVE.md before continuing execution?" 30)
assert_contains "$output" "design" "Mentions design link"
assert_contains "$output" "plan" "Mentions plan link"
assert_contains "$output" "context\|next step\|active" "Mentions context and next step"

echo ""

echo "Test 3: Task completion updates task records and wiki..."
output=$(run_claude "After completing one task in executing-plans, what records must be updated before moving on?" 30)
assert_contains "$output" "STATUS\.md\|ACTIVE\.md\|progress\|INDEX\.md" "Updates task state files"
assert_contains "$output" "wiki\|INDEX\.md\|project-wiki-maintenance\|no.*wiki.*update" "Mentions wiki maintenance or no-update record"

echo ""

echo "Test 4: Automatic completion archive..."
output=$(run_claude "When is an executing-plans run allowed to archive itself as completed?" 30)
assert_contains "$output" "all.*tasks" "Requires all tasks complete"
assert_contains "$output" "validation\|tests" "Requires validation"
assert_contains "$output" "wiki\|INDEX\.md\|knowledge" "Requires wiki work to be done"
assert_contains "$output" "docs/dev/completed\|completed/" "Moves task to completed directory"

echo ""
echo "=== All executing-plans skill tests passed ==="

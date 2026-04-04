#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "=== Test: project-wiki-maintenance skill ==="
echo ""

echo "Test 1: Skill loading..."
output=$(run_claude "What is the project-wiki-maintenance skill? Describe what it manages in this project." 30)
assert_contains "$output" "project-wiki-maintenance\|Project Wiki Maintenance\|wiki maintenance" "Skill is recognized"
assert_contains "$output" "wiki/\|project.*knowledge\|long-term.*knowledge" "Mentions project wiki scope"

echo ""

echo "Test 2: docs/wiki separation..."
output=$(run_claude "In project-wiki-maintenance, should execution logs and chat transcripts be written into wiki or kept elsewhere?" 30)
assert_contains "$output" "docs/dev\|kept.*elsewhere\|not.*wiki" "Separates docs from wiki"

echo ""

echo "Test 3: Long-lived knowledge must be written..."
output=$(run_claude "When a finished task produces a reusable rule or stable project convention, what does project-wiki-maintenance require?" 30)
assert_contains "$output" "must\|required" "Wiki update is required"
assert_contains "$output" "wiki/\|INDEX\.md\|index" "Mentions wiki and index updates"

echo ""

echo "Test 4: Module knowledge vs project experience..."
output=$(run_claude "How does project-wiki-maintenance decide between module documentation and cross-functional project experience?" 30)
assert_contains "$output" "module\|function" "Mentions module knowledge"
assert_contains "$output" "experience\|cross-functional" "Mentions project experience"

echo ""

echo "Test 5: No-wiki-update record stays in task docs..."
output=$(run_claude "If a task produces no lasting knowledge, where should project-wiki-maintenance record that fact?" 30)
assert_contains "$output" "STATUS\.md\|progress" "Records no-wiki-update in task docs"

echo ""
echo "=== All project-wiki-maintenance skill tests passed ==="

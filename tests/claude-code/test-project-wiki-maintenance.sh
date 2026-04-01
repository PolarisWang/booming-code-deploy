#!/usr/bin/env bash
# Test: project-wiki-maintenance skill
# Verifies project wiki knowledge handling and docs/wiki separation.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "=== Test: project-wiki-maintenance skill ==="
echo ""

echo "Test 1: Skill loading..."
output=$(run_claude "What is the project-wiki-maintenance skill? Describe what it manages in this project." 30)
assert_contains "$output" "project-wiki-maintenance\|Project Wiki Maintenance\|wiki maintenance" "Skill is recognized"
assert_contains "$output" "wiki/\|project.*knowledge\|长期.*知识\|long-term.*knowledge" "Mentions project wiki scope"

echo ""

echo "Test 2: docs/wiki separation..."
output=$(run_claude "In project-wiki-maintenance, should execution logs and chat transcripts be written into wiki or kept elsewhere?" 30)
assert_contains "$output" "docs\|executions\|kept.*elsewhere\|not.*wiki\|不写.*wiki" "Separates docs from wiki"

echo ""

echo "Test 3: Long-lived knowledge must be written..."
output=$(run_claude "When a finished task produces a reusable rule or stable project convention, what does project-wiki-maintenance require?" 30)
assert_contains "$output" "must\|required\|必须" "Wiki update is required"
assert_contains "$output" "wiki/\|INDEX\.md\|index" "Mentions wiki and index updates"

echo ""

echo "Test 4: Module knowledge vs project experience..."
output=$(run_claude "How does project-wiki-maintenance decide between wiki/03-功能模块 and wiki/05-项目经验?" 30)
assert_contains "$output" "功能\|module\|功能模块" "Mentions module knowledge"
assert_contains "$output" "经验\|experience\|跨功能\|cross-functional" "Mentions project experience"

echo ""
echo "=== All project-wiki-maintenance skill tests passed ==="

# Test: executing-plans skill (Windows PowerShell)
# Verifies execution context handling and wiki synchronization rules.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\test-helpers.ps1"

Write-Host "=== Test: executing-plans skill ===" -ForegroundColor Cyan
Write-Host ""

$failed = $false

Write-Host "Test 1: Counts plan tasks and creates CURRENT..."
$output = Run-Claude "In the executing-plans skill, what must happen at the start of execution regarding plan task count and docs/executions/CURRENT.md?" 30
if (-not (Assert-Contains $output "task.*count|count.*task|任务总数|number.*tasks" "Mentions task count")) { $failed = $true }
if (-not (Assert-Contains $output "CURRENT\.md|docs/executions/CURRENT\.md" "Mentions CURRENT.md")) { $failed = $true }

Write-Host ""

Write-Host "Test 2: CURRENT.md must capture structured context..."
$output = Run-Claude "What structured information should executing-plans record in docs/executions/CURRENT.md before continuing execution?" 30
if (-not (Assert-Contains $output "design|设计.*文档" "Mentions design link")) { $failed = $true }
if (-not (Assert-Contains $output "plan|计划.*文档" "Mentions plan link")) { $failed = $true }
if (-not (Assert-Contains $output "context|上下文|next step|下一步" "Mentions context and next step")) { $failed = $true }

Write-Host ""

Write-Host "Test 3: Task completion updates CURRENT and wiki..."
$output = Run-Claude "After completing one task in executing-plans, what records must be updated before moving on?" 30
if (-not (Assert-Contains $output "CURRENT\.md|docs/executions/CURRENT\.md" "Updates CURRENT")) { $failed = $true }
if (-not (Assert-Contains $output "wiki|INDEX\.md|project-wiki-maintenance|无 wiki 更新" "Mentions wiki maintenance or no-update record")) { $failed = $true }

Write-Host ""

Write-Host "Test 4: Automatic completion archive..."
$output = Run-Claude "When is an executing-plans run allowed to archive itself as completed?" 30
if (-not (Assert-Contains $output "all.*tasks|全部.*任务" "Requires all tasks complete")) { $failed = $true }
if (-not (Assert-Contains $output "validation|tests|验证" "Requires validation")) { $failed = $true }
if (-not (Assert-Contains $output "wiki|INDEX\.md|knowledge" "Requires wiki work to be done")) { $failed = $true }

Write-Host ""

if ($failed) {
    Write-Host "=== SOME TESTS FAILED ===" -ForegroundColor Red
    exit 1
} else {
    Write-Host "=== All executing-plans skill tests passed ===" -ForegroundColor Green
    exit 0
}

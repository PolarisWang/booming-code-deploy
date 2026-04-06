$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\test-helpers.ps1"

Write-Host "=== Test: executing-plans skill ===" -ForegroundColor Cyan
Write-Host ""

$failed = $false

Write-Host "Test 1: Counts plan tasks and creates task state..."
$output = Run-Claude "In the executing-plans skill, what must happen at the start of execution regarding plan task count, the task STATUS.md, and docs/dev/ACTIVE.md?" 30
if (-not (Assert-Contains $output "task.*count|count.*task|number.*tasks" "Mentions task count")) { $failed = $true }
if (-not (Assert-Contains $output "STATUS\.md|ACTIVE\.md|docs/dev/ACTIVE\.md" "Mentions STATUS and ACTIVE")) { $failed = $true }

Write-Host ""

Write-Host "Test 2: Active task conflicts must be blocked at skill entry..."
$output = Run-Claude "If docs/dev/ACTIVE.md already points to another task, what must executing-plans do before starting a new plan execution?" 30
if (-not (Assert-Contains $output "continue|hang|abandon" "Offers continue, hang, abandon")) { $failed = $true }
if (-not (Assert-Contains $output "block|stop|do not start|before starting" "Blocks new execution until handled")) { $failed = $true }

Write-Host ""

Write-Host "Test 3: Same-task resume and incomplete ACTIVE handling..."
$output = Run-Claude "If ACTIVE.md points to the same task, or if ACTIVE.md is incomplete, how should executing-plans behave?" 30
if (-not (Assert-Contains $output "resume|continue.*same task|恢复" "Resumes the same task")) { $failed = $true }
if (-not (Assert-Contains $output "cannot ignore|still treated as active|不能忽略" "Does not ignore incomplete ACTIVE")) { $failed = $true }

Write-Host ""

Write-Host "Test 4: STATUS.md and ACTIVE.md must capture structured context..."
$output = Run-Claude "What structured information should executing-plans record in the task STATUS.md and docs/dev/ACTIVE.md before continuing execution?" 30
if (-not (Assert-Contains $output "design" "Mentions design link")) { $failed = $true }
if (-not (Assert-Contains $output "plan" "Mentions plan link")) { $failed = $true }
if (-not (Assert-Contains $output "context|next step|active|total.*tasks" "Mentions context and next step")) { $failed = $true }

Write-Host ""

Write-Host "Test 5: Task completion updates task records and wiki..."
$output = Run-Claude "After completing one task in executing-plans, what records must be updated before moving on?" 30
if (-not (Assert-Contains $output "STATUS\.md|ACTIVE\.md|progress|INDEX\.md" "Updates task state files")) { $failed = $true }
if (-not (Assert-Contains $output "wiki|INDEX\.md|project-wiki-maintenance|no.*wiki.*update" "Mentions wiki maintenance or no-update record")) { $failed = $true }

Write-Host ""

Write-Host "Test 6: Automatic completion archive..."
$output = Run-Claude "When is an executing-plans run allowed to archive itself as completed?" 30
if (-not (Assert-Contains $output "all.*tasks" "Requires all tasks complete")) { $failed = $true }
if (-not (Assert-Contains $output "project.*test.*suite|full.*test|完整.*测试|项目.*测试" "Requires project test suite")) { $failed = $true }
if (-not (Assert-Contains $output "validation|tests" "Requires validation")) { $failed = $true }
if (-not (Assert-Contains $output "wiki|INDEX\.md|knowledge" "Requires wiki work to be done")) { $failed = $true }
if (-not (Assert-Contains $output "docs/dev/completed|completed/" "Moves task to completed directory")) { $failed = $true }

Write-Host ""

if ($failed) {
    Write-Host "=== SOME TESTS FAILED ===" -ForegroundColor Red
    exit 1
} else {
    Write-Host "=== All executing-plans skill tests passed ===" -ForegroundColor Green
    exit 0
}

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\test-helpers.ps1"

Write-Host "=== Test: roadmap skill ===" -ForegroundColor Cyan
Write-Host ""

$failed = $false

Write-Host "Test 1: Skill loading..."
$output = Run-Claude "What is the roadmap skill? Describe when it should be used." 30
if (-not (Assert-Contains $output "roadmap" "Skill is recognized")) { $failed = $true }
if (-not (Assert-Contains $output "phase|child task|multiple" "Mentions phases or child tasks")) { $failed = $true }

Write-Host ""

Write-Host "Test 2: Brainstorm routing..."
$output = Run-Claude "After brainstorming, when should a task go to roadmap instead of writing-plans?" 30
if (-not (Assert-Contains $output "multiple|phase|child task|stable implementation plan" "Mentions roadmap routing criteria")) { $failed = $true }

Write-Host ""

Write-Host "Test 3: Save location..."
$output = Run-Claude "Where should the roadmap document be saved in this project?" 30
if (-not (Assert-Contains $output "docs/dev/in-progress/.*/roadmap-v1-01\.md|roadmap-v1-01\.md" "Mentions roadmap path in task directory")) { $failed = $true }

Write-Host ""

Write-Host "Test 4: Parent task semantics..."
$output = Run-Claude "Is roadmap itself the implementation task, or should concrete work happen in child task directories?" 30
if (-not (Assert-Contains $output "child task|separate task director" "Mentions child task directories")) { $failed = $true }
if (-not (Assert-Contains $output "parent_task_id|roadmap-child" "Mentions parent-child linkage")) { $failed = $true }

Write-Host ""

if ($failed) {
    Write-Host "=== SOME TESTS FAILED ===" -ForegroundColor Red
    exit 1
} else {
    Write-Host "=== All roadmap skill tests passed ===" -ForegroundColor Green
    exit 0
}

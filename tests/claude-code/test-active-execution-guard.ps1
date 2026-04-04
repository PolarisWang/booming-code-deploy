$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\test-helpers.ps1"

Write-Host "=== Test: active-execution-guard skill ===" -ForegroundColor Cyan
Write-Host ""

$failed = $false

Write-Host "Test 1: Skill loading..."
$output = Run-Claude "What is the active-execution-guard skill? Describe when it should interrupt a normal conversation." 30
if (-not (Assert-Contains $output "active-execution-guard|Active Execution Guard|execution guard" "Skill is recognized")) { $failed = $true }
if (-not (Assert-Contains $output "ACTIVE\.md|docs/dev/ACTIVE\.md|active.*task|ongoing.*task" "Mentions active task file")) { $failed = $true }

Write-Host ""

Write-Host "Test 2: Allowed user choices..."
$output = Run-Claude "If docs/dev/ACTIVE.md exists, what options should active-execution-guard offer the user before any other answer?" 30
if (-not (Assert-Contains $output "继续|continue" "Mentions continue")) { $failed = $true }
if (-not (Assert-Contains $output "挂起|hang|suspend" "Mentions hang")) { $failed = $true }
if (-not (Assert-Contains $output "放弃|abandon|abandoned" "Mentions abandon")) { $failed = $true }
if (-not (Assert-NotContains $output "完成|complete it|mark.*complete|choose.*complete" "Does not offer complete")) { $failed = $true }

Write-Host ""

Write-Host "Test 3: Guard blocks unrelated answers..."
$output = Run-Claude "Can active-execution-guard answer a user's unrelated question before the active task is handled?" 30
if (-not (Assert-Contains $output "不|no|cannot|must not|should not" "Blocks unrelated answer")) { $failed = $true }

Write-Host ""

Write-Host "Test 4: ACTIVE.md cannot be ignored..."
$output = Run-Claude "If docs/dev/ACTIVE.md exists but looks incomplete, can active-execution-guard ignore it and continue anyway?" 30
if (-not (Assert-Contains $output "不|no|cannot|must not|still.*treat|completeness.*matter|existence.*means" "Incomplete ACTIVE is still active")) { $failed = $true }

Write-Host ""

if ($failed) {
    Write-Host "=== SOME TESTS FAILED ===" -ForegroundColor Red
    exit 1
} else {
    Write-Host "=== All active-execution-guard skill tests passed ===" -ForegroundColor Green
    exit 0
}

# Test: active-execution-guard skill (Windows PowerShell)
# Verifies that the skill is loaded and enforces active plan handling.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\test-helpers.ps1"

Write-Host "=== Test: active-execution-guard skill ===" -ForegroundColor Cyan
Write-Host ""

$failed = $false

Write-Host "Test 1: Skill loading..."
$output = Run-Claude "What is the active-execution-guard skill? Describe when it should interrupt a normal conversation." 30
if (-not (Assert-Contains $output "active-execution-guard|Active Execution Guard|execution guard" "Skill is recognized")) { $failed = $true }
if (-not (Assert-Contains $output "CURRENT\.md|docs/executions/CURRENT\.md|active.*plan|ongoing.*plan" "Mentions active execution file")) { $failed = $true }

Write-Host ""

Write-Host "Test 2: Allowed user choices..."
$output = Run-Claude "If docs/executions/CURRENT.md exists, what options should active-execution-guard offer the user before any other answer?" 30
if (-not (Assert-Contains $output "continue" "Mentions continue")) { $failed = $true }
if (-not (Assert-Contains $output "abandon|abandoned" "Mentions abandon")) { $failed = $true }
if (-not (Assert-NotContains $output "complete it|mark.*complete|choose.*complete" "Does not offer complete")) { $failed = $true }

Write-Host ""

Write-Host "Test 3: Guard blocks unrelated answers..."
$output = Run-Claude "Can active-execution-guard answer a user's unrelated question before the active plan is handled?" 30
if (-not (Assert-Contains $output "no|cannot|must not|should not" "Blocks unrelated answer")) { $failed = $true }

Write-Host ""

Write-Host "Test 4: CURRENT.md cannot be ignored..."
$output = Run-Claude "If docs/executions/CURRENT.md exists but looks incomplete, can active-execution-guard ignore it and continue anyway?" 30
if (-not (Assert-Contains $output "no|cannot|must not|still.*treat|completeness.*matter|existence.*means" "Incomplete CURRENT is still active")) { $failed = $true }

Write-Host ""

if ($failed) {
    Write-Host "=== SOME TESTS FAILED ===" -ForegroundColor Red
    exit 1
} else {
    Write-Host "=== All active-execution-guard skill tests passed ===" -ForegroundColor Green
    exit 0
}

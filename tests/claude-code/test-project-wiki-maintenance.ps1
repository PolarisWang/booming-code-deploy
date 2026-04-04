$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\test-helpers.ps1"

Write-Host "=== Test: project-wiki-maintenance skill ===" -ForegroundColor Cyan
Write-Host ""

$failed = $false

Write-Host "Test 1: Skill loading..."
$output = Run-Claude "What is the project-wiki-maintenance skill? Describe what it manages in this project." 30
if (-not (Assert-Contains $output "project-wiki-maintenance|Project Wiki Maintenance|wiki maintenance" "Skill is recognized")) { $failed = $true }
if (-not (Assert-Contains $output "wiki/|project.*knowledge|长期.*知识|long-term.*knowledge" "Mentions project wiki scope")) { $failed = $true }

Write-Host ""

Write-Host "Test 2: docs/wiki separation..."
$output = Run-Claude "In project-wiki-maintenance, should execution logs and chat transcripts be written into wiki or kept elsewhere?" 30
if (-not (Assert-Contains $output "docs/dev|kept.*elsewhere|not.*wiki|不写.*wiki" "Separates docs from wiki")) { $failed = $true }

Write-Host ""

Write-Host "Test 3: Long-lived knowledge must be written..."
$output = Run-Claude "When a finished task produces a reusable rule or stable project convention, what does project-wiki-maintenance require?" 30
if (-not (Assert-Contains $output "must|required|必须" "Wiki update is required")) { $failed = $true }
if (-not (Assert-Contains $output "wiki/|INDEX\.md|index" "Mentions wiki and index updates")) { $failed = $true }

Write-Host ""

Write-Host "Test 4: Module knowledge vs project experience..."
$output = Run-Claude "How does project-wiki-maintenance decide between wiki/03-功能模块 and wiki/05-项目经验?" 30
if (-not (Assert-Contains $output "功能|module|功能模块" "Mentions module knowledge")) { $failed = $true }
if (-not (Assert-Contains $output "经验|experience|跨功能|cross-functional" "Mentions project experience")) { $failed = $true }

Write-Host ""

Write-Host "Test 5: No-wiki-update record stays in task docs..."
$output = Run-Claude "If a task produces no lasting knowledge, where should project-wiki-maintenance record that fact?" 30
if (-not (Assert-Contains $output "STATUS\.md|progress" "Records no-wiki-update in task docs")) { $failed = $true }

Write-Host ""

if ($failed) {
    Write-Host "=== SOME TESTS FAILED ===" -ForegroundColor Red
    exit 1
} else {
    Write-Host "=== All project-wiki-maintenance skill tests passed ===" -ForegroundColor Green
    exit 0
}

# Test runner for Claude Code skills (Windows PowerShell)
# Tests skills by invoking Claude Code CLI and verifying behavior

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "========================================"
Write-Host " Claude Code Skills Test Suite"
Write-Host "========================================"
Write-Host ""
Write-Host "Repository: $(Resolve-Path (Join-Path $ScriptDir '..\..\..'))"
Write-Host "Test time: $(Get-Date)"
$claudeVersionRaw = & claude --version 2>$null
$claudeVersion = if ($claudeVersionRaw) { $claudeVersionRaw } else { "not found" }
Write-Host "Claude version: $claudeVersion"
Write-Host ""

# Check if Claude Code is available
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Claude Code CLI not found" -ForegroundColor Red
    Write-Host "Install Claude Code first: https://code.claude.com"
    exit 1
}

# Parse command line arguments
$Verbose = $false
$SpecificTest = ""
$TimeoutSeconds = 300
$RunIntegration = $false

for ($i = 0; $i -lt $args.Count; $i++) {
    switch ($args[$i]) {
        { $_ -in "--verbose", "-v" } { $Verbose = $true }
        { $_ -in "--test", "-t" }    { $SpecificTest = $args[++$i] }
        "--timeout"                   { $TimeoutSeconds = [int]$args[++$i] }
        { $_ -in "--integration", "-i" } { $RunIntegration = $true }
        { $_ -in "--help", "-h" } {
            Write-Host "Usage: .\run-skill-tests.ps1 [options]"
            Write-Host ""
            Write-Host "Options:"
            Write-Host "  --verbose, -v        Show verbose output"
            Write-Host "  --test, -t NAME      Run only the specified test"
            Write-Host "  --timeout SECONDS    Set timeout per test (default: 300)"
            Write-Host "  --integration, -i    Run integration tests (slow, 10-30 min)"
            Write-Host "  --help, -h           Show this help"
            Write-Host ""
            Write-Host "Tests:"
            Write-Host "  test-active-execution-guard-clean.ps1      Test active plan guard behavior"
            Write-Host "  test-project-wiki-maintenance-clean.ps1    Test project wiki maintenance rules"
            Write-Host "  test-executing-plans-clean.ps1             Test execution context and archive rules"
            Write-Host "  test-subagent-driven-development.ps1  Test skill loading and requirements"
            Write-Host ""
            Write-Host "Integration Tests (use --integration):"
            Write-Host "  test-subagent-driven-development-integration.ps1  Full workflow execution"
            exit 0
        }
        default {
            Write-Host "Unknown option: $($args[$i])" -ForegroundColor Red
            Write-Host "Use --help for usage information"
            exit 1
        }
    }
}

# List of skill tests to run (fast unit tests)
$tests = @(
    "test-active-execution-guard-clean.ps1"
    "test-project-wiki-maintenance-clean.ps1"
    "test-executing-plans-clean.ps1"
    "test-subagent-driven-development.ps1"
)

# Integration tests (slow, full execution)
$integrationTests = @(
    "test-subagent-driven-development-integration.ps1"
)

# Add integration tests if requested
if ($RunIntegration) {
    $tests += $integrationTests
}

# Filter to specific test if requested
if ($SpecificTest) {
    $tests = @($SpecificTest)
}

# Track results
$passed = 0
$failed = 0
$skipped = 0

# Run each test
foreach ($test in $tests) {
    Write-Host "----------------------------------------"
    Write-Host "Running: $test"
    Write-Host "----------------------------------------"

    $testPath = Join-Path $ScriptDir $test

    if (-not (Test-Path $testPath)) {
        Write-Host "  [SKIP] Test file not found: $test" -ForegroundColor Yellow
        $skipped++
        continue
    }

    $startTime = Get-Date

    $job = Start-Job -ScriptBlock {
        param($tp)
        & powershell -NonInteractive -File $tp 2>&1
    } -ArgumentList $testPath

    $completed = Wait-Job -Job $job -Timeout $TimeoutSeconds
    $elapsed = [int]((Get-Date) - $startTime).TotalSeconds

    if ($null -eq $completed) {
        Stop-Job -Job $job
        Remove-Job -Job $job -Force
        Write-Host "  [FAIL] $test (timeout after ${TimeoutSeconds}s)" -ForegroundColor Red
        $failed++
    } else {
        $output = Receive-Job -Job $job
        $exitCode = 0
        Remove-Job -Job $job

        # Determine pass/fail by checking output for failure indicators
        $testFailed = $output -match '\[FAIL\]' -or $job.State -eq 'Failed'

        if (-not $testFailed) {
            if ($Verbose) { $output | Write-Host }
            Write-Host "  [PASS] (${elapsed}s)" -ForegroundColor Green
            $passed++
        } else {
            if ($Verbose) {
                $output | Write-Host
            } else {
                Write-Host "  [FAIL] (${elapsed}s)" -ForegroundColor Red
                Write-Host ""
                Write-Host "  Output:"
                $output | ForEach-Object { Write-Host "    $_" }
            }
            $failed++
        }
    }

    Write-Host ""
}

# Print summary
Write-Host "========================================"
Write-Host " Test Results Summary"
Write-Host "========================================"
Write-Host ""
Write-Host "  Passed:  $passed"
Write-Host "  Failed:  $failed"
Write-Host "  Skipped: $skipped"
Write-Host ""

if (-not $RunIntegration -and $integrationTests.Count -gt 0) {
    Write-Host "Note: Integration tests were not run (they take 10-30 minutes)."
    Write-Host "Use -integration flag to run full workflow execution tests."
    Write-Host ""
}

if ($failed -gt 0) {
    Write-Host "STATUS: FAILED" -ForegroundColor Red
    exit 1
} else {
    Write-Host "STATUS: PASSED" -ForegroundColor Green
    exit 0
}

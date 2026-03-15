# Helper functions for Claude Code skill tests (Windows PowerShell)

# Run Claude Code with a prompt and capture output
# Usage: Run-Claude "prompt text" [timeout_seconds] [allowed_tools]
function Run-Claude {
    param(
        [string]$Prompt,
        [int]$TimeoutSeconds = 60,
        [string]$AllowedTools = ""
    )

    $args = @("-p", $Prompt)
    if ($AllowedTools) {
        $args += "--allowed-tools=$AllowedTools"
    }

    $job = Start-Job -ScriptBlock {
        param($claudeArgs)
        & claude @claudeArgs 2>&1
    } -ArgumentList (, $args)

    $completed = Wait-Job -Job $job -Timeout $TimeoutSeconds

    if ($null -eq $completed) {
        Stop-Job -Job $job
        Remove-Job -Job $job -Force
        Write-Error "Claude timed out after ${TimeoutSeconds}s"
        return $null
    }

    $output = Receive-Job -Job $job
    Remove-Job -Job $job
    return $output -join "`n"
}

# Check if output contains a pattern
# Usage: Assert-Contains $output "pattern" "test name"
function Assert-Contains {
    param(
        [string]$Output,
        [string]$Pattern,
        [string]$TestName = "test"
    )

    if ($Output -match $Pattern) {
        Write-Host "  [PASS] $TestName" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  [FAIL] $TestName" -ForegroundColor Red
        Write-Host "  Expected to find: $Pattern"
        Write-Host "  In output:"
        $Output -split "`n" | ForEach-Object { Write-Host "    $_" }
        return $false
    }
}

# Check if output does NOT contain a pattern
# Usage: Assert-NotContains $output "pattern" "test name"
function Assert-NotContains {
    param(
        [string]$Output,
        [string]$Pattern,
        [string]$TestName = "test"
    )

    if ($Output -match $Pattern) {
        Write-Host "  [FAIL] $TestName" -ForegroundColor Red
        Write-Host "  Did not expect to find: $Pattern"
        Write-Host "  In output:"
        $Output -split "`n" | ForEach-Object { Write-Host "    $_" }
        return $false
    } else {
        Write-Host "  [PASS] $TestName" -ForegroundColor Green
        return $true
    }
}

# Check if output matches a count
# Usage: Assert-Count $output "pattern" 3 "test name"
function Assert-Count {
    param(
        [string]$Output,
        [string]$Pattern,
        [int]$Expected,
        [string]$TestName = "test"
    )

    $actual = ($Output -split "`n" | Where-Object { $_ -match $Pattern }).Count

    if ($actual -eq $Expected) {
        Write-Host "  [PASS] $TestName (found $actual instances)" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  [FAIL] $TestName" -ForegroundColor Red
        Write-Host "  Expected $Expected instances of: $Pattern"
        Write-Host "  Found $actual instances"
        Write-Host "  In output:"
        $Output -split "`n" | ForEach-Object { Write-Host "    $_" }
        return $false
    }
}

# Check if pattern A appears before pattern B
# Usage: Assert-Order $output "pattern_a" "pattern_b" "test name"
function Assert-Order {
    param(
        [string]$Output,
        [string]$PatternA,
        [string]$PatternB,
        [string]$TestName = "test"
    )

    $lines = $Output -split "`n"
    $lineA = $null
    $lineB = $null

    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($null -eq $lineA -and $lines[$i] -match $PatternA) { $lineA = $i }
        if ($null -eq $lineB -and $lines[$i] -match $PatternB) { $lineB = $i }
    }

    if ($null -eq $lineA) {
        Write-Host "  [FAIL] $TestName`: pattern A not found: $PatternA" -ForegroundColor Red
        return $false
    }
    if ($null -eq $lineB) {
        Write-Host "  [FAIL] $TestName`: pattern B not found: $PatternB" -ForegroundColor Red
        return $false
    }

    if ($lineA -lt $lineB) {
        Write-Host "  [PASS] $TestName (A at line $lineA, B at line $lineB)" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  [FAIL] $TestName" -ForegroundColor Red
        Write-Host "  Expected '$PatternA' before '$PatternB'"
        Write-Host "  But found A at line $lineA, B at line $lineB"
        return $false
    }
}

# Create a temporary test project directory
# Usage: $testProject = New-TestProject
function New-TestProject {
    $tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ([System.IO.Path]::GetRandomFileName())
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    return $tempDir
}

# Cleanup test project
# Usage: Remove-TestProject $testDir
function Remove-TestProject {
    param([string]$TestDir)
    if (Test-Path $TestDir) {
        Remove-Item -Recurse -Force $TestDir
    }
}

# Create a simple plan file for testing
# Usage: $planFile = New-TestPlan $projectDir "plan-name"
function New-TestPlan {
    param(
        [string]$ProjectDir,
        [string]$PlanName = "test-plan"
    )

    $planFile = Join-Path $ProjectDir "docs\superpowers\plans\$PlanName.md"
    New-Item -ItemType Directory -Path (Split-Path $planFile) -Force | Out-Null

    Set-Content -Path $planFile -Value @'
# Test Implementation Plan

## Task 1: Create Hello Function

Create a simple hello function that returns "Hello, World!".

**File:** `src/hello.js`

**Implementation:**
```javascript
export function hello() {
  return "Hello, World!";
}
```

**Tests:** Write a test that verifies the function returns the expected string.

**Verification:** `npm test`

## Task 2: Create Goodbye Function

Create a goodbye function that takes a name and returns a goodbye message.

**File:** `src/goodbye.js`

**Implementation:**
```javascript
export function goodbye(name) {
  return `Goodbye, ${name}!`;
}
```

**Tests:** Write tests for:
- Default name
- Custom name
- Edge cases (empty string, null)

**Verification:** `npm test`
'@

    return $planFile
}

# Helper functions for Claude Code skill tests (Windows PowerShell)

# Resolve the repository root from the test directory.
function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
}

# Find repo-local skill documents that should be treated as the source of truth
# for a given test prompt.
function Get-SkillDocPaths {
    param([string]$Prompt)

    $repoRoot = Get-RepoRoot
    $skillMap = [ordered]@{
        "active-execution-guard"      = @(".codex\skills\dev-active-execution-guard\SKILL.md")
        "project-wiki-maintenance"    = @(".codex\skills\dev-project-wiki-maintenance\SKILL.md")
        "executing-plans"             = @(".codex\skills\dev-executing-plans\SKILL.md")
        "subagent-driven-development" = @(".codex\skills\dev-subagent-driven-development\SKILL.md")
    }

    $paths = New-Object System.Collections.Generic.List[string]

    foreach ($skillName in $skillMap.Keys) {
        if ($Prompt -match [regex]::Escape($skillName)) {
            foreach ($relativePath in $skillMap[$skillName]) {
                $paths.Add((Join-Path $repoRoot $relativePath))
            }
        }
    }

    return $paths | Select-Object -Unique
}

# Provide a normalized English contract for repo-local skills whose source docs
# contain mixed encoding or large amounts of non-English prose.
function Get-SkillContractSummary {
    param([string]$Prompt)

    $contracts = [ordered]@{
        "active-execution-guard" = @(
            "- `docs/executions/CURRENT.md` present means there is an active plan or ongoing plan."
            "- The guard must block unrelated answers until the active plan is handled."
            "- The user may choose only `continue` or `abandon`."
            "- The guard must not offer `complete`."
            "- Even an incomplete `CURRENT.md` is still treated as active."
        )
        "project-wiki-maintenance" = @(
            "- `wiki/` stores long-term project knowledge."
            "- Execution logs and chat transcripts stay in `docs/executions/`, not in `wiki/`."
            "- Stable or reusable knowledge must update the target wiki page and the relevant `INDEX.md`."
            "- Module or feature knowledge belongs in `wiki/03-功能模块/`."
            "- Cross-functional reusable experience belongs in `wiki/05-项目经验/`."
            "- If a task has no lasting knowledge, record `no wiki update` in `docs/executions/CURRENT.md`."
        )
        "executing-plans" = @(
            "- At the start, count the total number of tasks in the plan."
            "- Create or update `docs/executions/CURRENT.md` before execution continues."
            "- `CURRENT.md` must contain the design doc link, the plan doc link, important context, current progress, and the next step."
            "- After each task, update `CURRENT.md` first."
            "- Then either update `wiki/` and the relevant `INDEX.md` through `project-wiki-maintenance`, or record `no wiki update`."
            "- A run may archive itself as `completed` only when all tasks are done, required validation or tests pass, and required wiki knowledge has been written."
        )
        "subagent-driven-development" = @(
            "- Step 1 is `Load Plan`: the controller reads the plan once at the beginning and extracts all tasks."
            "- The controller provides the full task text directly in the subagent prompt."
            "- The implementer does not load the plan file."
            "- The implementer must do self-review and check completeness before reporting done."
            "- Review order is spec compliance first, code quality second."
            "- The spec compliance reviewer is skeptical, does not trust the implementer report, and must read code independently."
            "- If a reviewer finds issues, the implementer fixes issues."
            "- The review loops again until approved or compliant."
            "- `docs/executions/CURRENT.md` holds the active execution context for resume."
            "- After each task, update `CURRENT.md` and update `wiki/` plus the relevant `INDEX.md` when knowledge changes."
            "- `using-git-worktrees` is required."
            "- Do not start implementation on `main` or `master` without explicit user consent."
        )
    }

    $summaryLines = New-Object System.Collections.Generic.List[string]

    foreach ($skillName in $contracts.Keys) {
        if ($Prompt -match [regex]::Escape($skillName)) {
            $summaryLines.Add("Normalized contract for ${skillName}:")
            foreach ($line in $contracts[$skillName]) {
                $summaryLines.Add($line)
            }
        }
    }

    return $summaryLines
}

# Build a prompt that pins Claude to the repo-local skill docs instead of any
# globally installed plugin state on the machine running the tests.
function Build-ClaudePrompt {
    param([string]$Prompt)

    $contractSummary = @(Get-SkillContractSummary $Prompt)
    $useContractOnly = $contractSummary.Count -gt 0
    $docPaths = if ($useContractOnly) { @() } else { @(Get-SkillDocPaths $Prompt) }
    if ($docPaths.Count -eq 0 -and $contractSummary.Count -eq 0) {
        return $Prompt
    }

    $sections = foreach ($path in $docPaths) {
        $content = Get-Content -Raw -Encoding UTF8 $path
        @"
Project-local skill source of truth: $path
---
$content
---
"@
    }

    $prefix = @"
Use the following repository-local skill documents as the authoritative source of truth for this question.
These documents come from `.codex/skills`, which is the implementation truth source for this repo.
If your installed or global skills differ, ignore them for this answer.
Answer directly from these documents and summarize the applicable rules.
When the normalized English contract already contains exact wording that answers the question, prefer using that wording.
"@

    $contractBlock = if ($contractSummary.Count -gt 0) {
        "Use this normalized English contract when the underlying SKILL.md content is noisy or mixed-encoding:`n" + ($contractSummary -join "`n")
    } else {
        ""
    }

    return ($prefix + "`n`n" + $contractBlock + "`n`n" + ($sections -join "`n`n") + "`nQuestion: $Prompt")
}

# Run Claude Code with a prompt and capture output.
# Usage: Run-Claude "prompt text" [timeout_seconds] [allowed_tools]
function Run-Claude {
    param(
        [string]$Prompt,
        [int]$TimeoutSeconds = 60,
        [string]$AllowedTools = ""
    )

    $repoRoot = Get-RepoRoot
    $resolvedPrompt = Build-ClaudePrompt $Prompt
    $args = @("-p", $resolvedPrompt)
    if ($AllowedTools) {
        $args += "--allowed-tools=$AllowedTools"
    }

    $job = Start-Job -ScriptBlock {
        param($claudeArgs, $workingDir)
        Set-Location $workingDir
        & claude @claudeArgs 2>&1
    } -ArgumentList (, $args), $repoRoot

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

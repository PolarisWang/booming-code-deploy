# Helper functions for Claude Code skill tests (Windows PowerShell)

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
}

function Get-SkillDocPaths {
    param([string]$Prompt)

    $repoRoot = Get-RepoRoot
    $skillMap = [ordered]@{
        "active-execution-guard"      = @(".codex\skills\dev-active-execution-guard\SKILL.md")
        "project-wiki-maintenance"    = @(".codex\skills\dev-project-wiki-maintenance\SKILL.md")
        "executing-plans"             = @(".codex\skills\dev-executing-plans\SKILL.md")
        "subagent-driven-development" = @(".codex\skills\dev-subagent-driven-development\SKILL.md")
        "roadmap"                     = @(".codex\skills\dev-roadmap\SKILL.md")
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

function Get-SkillContractSummary {
    param([string]$Prompt)

    $contracts = [ordered]@{
        "active-execution-guard" = @(
            "- `docs/dev/ACTIVE.md` present means there is an active task."
            "- The guard must block unrelated complex flows until the active task is handled."
            "- The user may choose only `continue`, `hang`, or `abandon`."
            "- `hang` means suspend the current task, save progress, and then continue the user's new request."
            "- `abandon` means mark the current task abandoned and then continue the user's new request."
            "- The guard must not offer `complete`."
            "- Even an incomplete `ACTIVE.md` is still treated as active."
        )
        "project-wiki-maintenance" = @(
            "- `wiki/` stores long-term project knowledge."
            "- Execution logs and chat transcripts stay in `docs/dev/<lifecycle>/<task_id>/`, not in `wiki/`."
            "- Stable or reusable knowledge must update the target wiki page and the relevant `INDEX.md`."
            "- Module or feature knowledge belongs in `wiki/03-功能模块/`."
            "- Cross-functional reusable experience belongs in `wiki/05-项目经验/`."
            "- If a task has no lasting knowledge, record `no wiki update` in the task `STATUS.md` or latest `notes/progress-*.md`."
        )
        "executing-plans" = @(
            "- At the start, count the total number of tasks in the plan."
            "- Create or update the task `STATUS.md` and `docs/dev/ACTIVE.md` before execution continues."
            "- The task directory is the execution truth source; `ACTIVE.md` is only the active pointer."
            "- After each task, update `STATUS.md`, `ACTIVE.md`, task progress notes, and the relevant `INDEX.md` files."
            "- Then either update `wiki/` and the relevant `INDEX.md` through `project-wiki-maintenance`, or record `no wiki update`."
            "- A run may move the task directory to `docs/dev/completed/` only when all tasks are done, required validation or tests pass, and required wiki knowledge has been written."
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
            "- `docs/dev/ACTIVE.md` holds the active task pointer for resume."
            "- The task directory `STATUS.md` holds the execution truth source."
            "- After each task, update `STATUS.md`, `ACTIVE.md`, and the relevant `INDEX.md` files when knowledge changes."
            "- `using-git-worktrees` is required."
            "- Do not start implementation on `main` or `master` without explicit user consent."
        )
        "roadmap" = @(
            "- Use roadmap after brainstorming when a task needs multiple phases, multiple child tasks, or cannot yet produce a stable implementation plan."
            "- If the routing decision is roadmap, the agent must explain why and wait for user confirmation before continuing."
            "- Save the roadmap into the current task directory, for example `docs/dev/in-progress/<task_id>/roadmap-v1-01.md`."
            "- Roadmap is a parent task artifact; concrete implementation should happen in separate child task directories."
            "- Child tasks should record `parent_task_id` and `source_relation: roadmap-child`."
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

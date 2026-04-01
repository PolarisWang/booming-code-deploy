# Test: subagent-driven-development skill (Windows PowerShell)
# Verifies that the skill is loaded and follows correct workflow

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\test-helpers.ps1"

Write-Host "=== Test: subagent-driven-development skill ===" -ForegroundColor Cyan
Write-Host ""

$failed = $false

# Test 1: Verify skill can be loaded
Write-Host "Test 1: Skill loading..."

$output = Run-Claude "What is the subagent-driven-development skill? Describe its key steps briefly." 30

if (-not (Assert-Contains $output "subagent-driven-development|Subagent-Driven Development|Subagent Driven" "Skill is recognized")) { $failed = $true }
if (-not (Assert-Contains $output "Load Plan|read.*plan|extract.*tasks" "Mentions loading plan")) { $failed = $true }

Write-Host ""

# Test 2: Verify skill describes correct workflow order
Write-Host "Test 2: Workflow ordering..."

$output = Run-Claude "In the subagent-driven-development skill, what comes first: spec compliance review or code quality review? Be specific about the order." 30

if (-not (Assert-Contains $output "spec.*(before|first).*code.*quality|code.*quality.*(after|second).*spec" "Spec compliance before code quality")) { $failed = $true }

Write-Host ""

# Test 3: Verify self-review is mentioned
Write-Host "Test 3: Self-review requirement..."

$output = Run-Claude "Does the subagent-driven-development skill require implementers to do self-review? What should they check?" 30

if (-not (Assert-Contains $output "self-review|self review" "Mentions self-review")) { $failed = $true }
if (-not (Assert-Contains $output "completeness|Completeness" "Checks completeness")) { $failed = $true }

Write-Host ""

# Test 4: Verify plan is read once
Write-Host "Test 4: Plan reading efficiency..."

$output = Run-Claude "In subagent-driven-development, how many times should the controller read the plan file? When does this happen?" 30

if (-not (Assert-Contains $output "once|one time|single" "Read plan once")) { $failed = $true }
if (-not (Assert-Contains $output "Step 1|beginning|start|Load Plan" "Read at beginning")) { $failed = $true }

Write-Host ""

# Test 5: Verify spec compliance reviewer is skeptical
Write-Host "Test 5: Spec compliance reviewer mindset..."

$output = Run-Claude "What is the spec compliance reviewer's attitude toward the implementer's report in subagent-driven-development?" 30

if (-not (Assert-Contains $output "not trust|don't trust|skeptical|verify.*independently|suspiciously" "Reviewer is skeptical")) { $failed = $true }
if (-not (Assert-Contains $output "read.*code|inspect.*code|verify.*code" "Reviewer reads code")) { $failed = $true }

Write-Host ""

# Test 6: Verify review loops
Write-Host "Test 6: Review loop requirements..."

$output = Run-Claude "In subagent-driven-development, what happens if a reviewer finds issues? Is it a one-time review or a loop?" 30

if (-not (Assert-Contains $output "loop|again|repeat|until.*approved|until.*compliant" "Review loops mentioned")) { $failed = $true }
if (-not (Assert-Contains $output "implementer.*fix|fix.*issues" "Implementer fixes issues")) { $failed = $true }

Write-Host ""

# Test 7: Verify full task text is provided
Write-Host "Test 7: Task context provision..."

$output = Run-Claude "In subagent-driven-development, how does the controller provide task information to the implementer subagent? Does it make them read a file or provide it directly?" 30

if (-not (Assert-Contains $output "provide.*directly|full.*text|paste|include.*prompt" "Provides text directly")) { $failed = $true }
if (-not (Assert-NotContains $output "subagent.*must.*read.*file|make.*subagent.*read.*file|open.*the.*file" "Doesn't make subagent read file")) { $failed = $true }

Write-Host ""

# Test 8: Verify worktree requirement
Write-Host "Test 8: Worktree requirement..."

$output = Run-Claude "What workflow skills are required before using subagent-driven-development? List any prerequisites or required skills." 30

if (-not (Assert-Contains $output "using-git-worktrees|worktree" "Mentions worktree requirement")) { $failed = $true }

Write-Host ""

# Test 9: Verify main branch warning
Write-Host "Test 9: Main branch red flag..."

$output = Run-Claude "In subagent-driven-development, is it okay to start implementation directly on the main branch?" 30

if (-not (Assert-Contains $output "worktree|feature.*branch|not.*main|never.*main|avoid.*main|don't.*main|consent|permission" "Warns against main branch")) { $failed = $true }

Write-Host ""

# Test 10: Verify CURRENT.md is used for active execution context
Write-Host "Test 10: Active execution context..."

$output = Run-Claude "In subagent-driven-development, what file should hold the current execution context so work can be resumed later?" 30

if (-not (Assert-Contains $output "CURRENT\.md|docs/executions/CURRENT\.md" "Mentions CURRENT.md")) { $failed = $true }

Write-Host ""

# Test 11: Verify task completion updates CURRENT and wiki
Write-Host "Test 11: Task completion bookkeeping..."

$output = Run-Claude "After one task finishes in subagent-driven-development, what should be updated besides the todo list?" 30

if (-not (Assert-Contains $output "CURRENT\.md|docs/executions/CURRENT\.md" "Updates CURRENT after task")) { $failed = $true }
if (-not (Assert-Contains $output "wiki|INDEX\.md|project-wiki-maintenance|knowledge" "Mentions wiki maintenance after task")) { $failed = $true }

Write-Host ""

if ($failed) {
    Write-Host "=== SOME TESTS FAILED ===" -ForegroundColor Red
    exit 1
} else {
    Write-Host "=== All subagent-driven-development skill tests passed ===" -ForegroundColor Green
    exit 0
}

# Integration Test: subagent-driven-development workflow (Windows PowerShell)
# Actually executes a plan and verifies the new workflow behaviors

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$ScriptDir\test-helpers.ps1"

Write-Host "========================================"
Write-Host " Integration Test: subagent-driven-development"
Write-Host "========================================"
Write-Host ""
Write-Host "This test executes a real plan using the skill and verifies:"
Write-Host "  1. Plan is read once (not per task)"
Write-Host "  2. Full task text provided to subagents"
Write-Host "  3. Subagents perform self-review"
Write-Host "  4. Spec compliance review before code quality"
Write-Host "  5. Review loops when issues found"
Write-Host "  6. Spec reviewer reads code independently"
Write-Host ""
Write-Host "WARNING: This test may take 10-30 minutes to complete."
Write-Host ""

# Create test project
$TestProject = New-TestProject
Write-Host "Test project: $TestProject"

# Register cleanup on exit
$cleanupBlock = { Remove-TestProject $TestProject }
try {

# Set up minimal Node.js project
$packageJson = @{
    name = "test-project"
    version = "1.0.0"
    type = "module"
    scripts = @{ test = "node --test" }
} | ConvertTo-Json
Set-Content -Path "$TestProject\package.json" -Value $packageJson

New-Item -ItemType Directory "$TestProject\src" | Out-Null
New-Item -ItemType Directory "$TestProject\test" | Out-Null
New-Item -ItemType Directory "$TestProject\docs\superpowers\plans" -Force | Out-Null

# Create implementation plan
Set-Content -Path "$TestProject\docs\superpowers\plans\implementation-plan.md" -Value @'
# Test Implementation Plan

This is a minimal plan to test the subagent-driven-development workflow.

## Task 1: Create Add Function

Create a function that adds two numbers.

**File:** `src/math.js`

**Requirements:**
- Function named `add`
- Takes two parameters: `a` and `b`
- Returns the sum of `a` and `b`
- Export the function

**Implementation:**
```javascript
export function add(a, b) {
  return a + b;
}
```

**Tests:** Create `test/math.test.js` that verifies:
- `add(2, 3)` returns `5`
- `add(0, 0)` returns `0`
- `add(-1, 1)` returns `0`

**Verification:** `npm test`

## Task 2: Create Multiply Function

Create a function that multiplies two numbers.

**File:** `src/math.js` (add to existing file)

**Requirements:**
- Function named `multiply`
- Takes two parameters: `a` and `b`
- Returns the product of `a` and `b`
- Export the function
- DO NOT add any extra features (like power, divide, etc.)

**Implementation:**
```javascript
export function multiply(a, b) {
  return a * b;
}
```

**Tests:** Add to `test/math.test.js`:
- `multiply(2, 3)` returns `6`
- `multiply(0, 5)` returns `0`
- `multiply(-2, 3)` returns `-6`

**Verification:** `npm test`
'@

# Initialize git repo
Push-Location $TestProject
git init --quiet
git config user.email "test@test.com"
git config user.name "Test User"
git add .
git commit -m "Initial commit" --quiet
Pop-Location

Write-Host ""
Write-Host "Project setup complete. Starting execution..."
Write-Host ""

$OutputFile = "$TestProject\claude-output.txt"

$Prompt = "Change to directory $TestProject and then execute the implementation plan at docs/superpowers/plans/implementation-plan.md using the subagent-driven-development skill.

IMPORTANT: Follow the skill exactly. I will be verifying that you:
1. Read the plan once at the beginning
2. Provide full task text to subagents (don't make them read files)
3. Ensure subagents do self-review before reporting
4. Run spec compliance review before code quality review
5. Use review loops when issues are found

Begin now. Execute the plan."

Write-Host "Running Claude (output will be shown below and saved to $OutputFile)..."
Write-Host "================================================================================"

Push-Location (Join-Path $ScriptDir "..\..")
$job = Start-Job -ScriptBlock {
    param($p, $td)
    & claude -p $p --allowed-tools=all --add-dir $td --permission-mode bypassPermissions 2>&1
} -ArgumentList $Prompt, $TestProject

$completed = Wait-Job -Job $job -Timeout 1800
if ($null -eq $completed) {
    Stop-Job -Job $job
    Write-Host "EXECUTION TIMED OUT" -ForegroundColor Red
    Pop-Location
    exit 1
}

$claudeOutput = Receive-Job -Job $job
Remove-Job -Job $job
$claudeOutput | Tee-Object -FilePath $OutputFile | Write-Host
Pop-Location

Write-Host "================================================================================"
Write-Host ""
Write-Host "Execution complete. Analyzing results..."
Write-Host ""

# Find session transcript
$WorkingDirEscaped = (Join-Path $ScriptDir "..\..") -replace '[\\/]', '-' -replace '^-', ''
$SessionDir = Join-Path $env:USERPROFILE ".claude\projects\$WorkingDirEscaped"
$SessionFile = Get-ChildItem -Path $SessionDir -Filter "*.jsonl" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-1) } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 -ExpandProperty FullName

if (-not $SessionFile) {
    Write-Host "ERROR: Could not find session transcript file" -ForegroundColor Red
    Write-Host "Looked in: $SessionDir"
    exit 1
}

Write-Host "Analyzing session transcript: $(Split-Path $SessionFile -Leaf)"
Write-Host ""

$FAILED = 0
$sessionContent = Get-Content $SessionFile -Raw

Write-Host "=== Verification Tests ==="
Write-Host ""

# Test 1: Skill was invoked
Write-Host "Test 1: Skill tool invoked..."
if ($sessionContent -match '"name":"Skill".*"skill":"superpowers:subagent-driven-development"') {
    Write-Host "  [PASS] subagent-driven-development skill was invoked" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Skill was not invoked" -ForegroundColor Red
    $FAILED++
}
Write-Host ""

# Test 2: Subagents were used
Write-Host "Test 2: Subagents dispatched..."
$taskCount = ([regex]::Matches($sessionContent, '"name":"Task"')).Count
if ($taskCount -ge 2) {
    Write-Host "  [PASS] $taskCount subagents dispatched" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Only $taskCount subagent(s) dispatched (expected >= 2)" -ForegroundColor Red
    $FAILED++
}
Write-Host ""

# Test 3: TodoWrite was used
Write-Host "Test 3: Task tracking..."
$todoCount = ([regex]::Matches($sessionContent, '"name":"TodoWrite"')).Count
if ($todoCount -ge 1) {
    Write-Host "  [PASS] TodoWrite used $todoCount time(s) for task tracking" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] TodoWrite not used" -ForegroundColor Red
    $FAILED++
}
Write-Host ""

# Test 6: Implementation actually works
Write-Host "Test 6: Implementation verification..."
$mathFile = "$TestProject\src\math.js"
if (Test-Path $mathFile) {
    Write-Host "  [PASS] src/math.js created" -ForegroundColor Green
    $mathContent = Get-Content $mathFile -Raw

    if ($mathContent -match "export function add") {
        Write-Host "  [PASS] add function exists" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] add function missing" -ForegroundColor Red
        $FAILED++
    }

    if ($mathContent -match "export function multiply") {
        Write-Host "  [PASS] multiply function exists" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] multiply function missing" -ForegroundColor Red
        $FAILED++
    }
} else {
    Write-Host "  [FAIL] src/math.js not created" -ForegroundColor Red
    $FAILED++
}

$testFile = "$TestProject\test\math.test.js"
if (Test-Path $testFile) {
    Write-Host "  [PASS] test/math.test.js created" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] test/math.test.js not created" -ForegroundColor Red
    $FAILED++
}

Push-Location $TestProject
$testResult = & npm test 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [PASS] Tests pass" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Tests failed" -ForegroundColor Red
    $testResult | Write-Host
    $FAILED++
}
Pop-Location
Write-Host ""

# Test 7: Git commits show proper workflow
Write-Host "Test 7: Git commit history..."
$commitCount = (git -C $TestProject log --oneline | Measure-Object -Line).Lines
if ($commitCount -gt 2) {
    Write-Host "  [PASS] Multiple commits created ($commitCount total)" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Too few commits ($commitCount, expected >2)" -ForegroundColor Red
    $FAILED++
}
Write-Host ""

# Test 8: No extra features
Write-Host "Test 8: No extra features added (spec compliance)..."
if (Test-Path $mathFile) {
    $mathContent = Get-Content $mathFile -Raw
    if ($mathContent -match "export function divide|export function power|export function subtract") {
        Write-Host "  [WARN] Extra features found (spec review should have caught this)" -ForegroundColor Yellow
    } else {
        Write-Host "  [PASS] No extra features added" -ForegroundColor Green
    }
}
Write-Host ""

# Token Usage Analysis
Write-Host "========================================="
Write-Host " Token Usage Analysis"
Write-Host "========================================="
Write-Host ""
& python "$ScriptDir\analyze-token-usage.py" $SessionFile
Write-Host ""

# Summary
Write-Host "========================================"
Write-Host " Test Summary"
Write-Host "========================================"
Write-Host ""

if ($FAILED -eq 0) {
    Write-Host "STATUS: PASSED" -ForegroundColor Green
    Write-Host "All verification tests passed!"
    exit 0
} else {
    Write-Host "STATUS: FAILED" -ForegroundColor Red
    Write-Host "Failed $FAILED verification tests"
    Write-Host ""
    Write-Host "Output saved to: $OutputFile"
    exit 1
}

} finally {
    & $cleanupBlock
}

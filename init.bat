@echo off
setlocal enabledelayedexpansion

REM Get .claude parent directory
for %%I in ("%~dp0..") do set "PARENT_DIR=%%~fI"

REM ============================================================
REM Step 1: Check and set ANTHROPIC_AUTH_TOKEN
REM ============================================================

set "NEED_SETUP=1"

reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v ANTHROPIC_AUTH_TOKEN >nul 2>&1
if %ERRORLEVEL% EQU 0 set "NEED_SETUP=0"

if "%NEED_SETUP%"=="1" (
    reg query "HKCU\Environment" /v ANTHROPIC_AUTH_TOKEN >nul 2>&1
    if !ERRORLEVEL! EQU 0 set "NEED_SETUP=0"
)

if "%NEED_SETUP%"=="1" (
    echo.
    echo  ANTHROPIC_AUTH_TOKEN not found in environment.
    echo.
    set /p "INPUT_TOKEN=  Enter ANTHROPIC_AUTH_TOKEN : "
    set /p "INPUT_URL=  Enter ANTHROPIC_BASE_URL   : "
    echo.

    setx /M ANTHROPIC_AUTH_TOKEN "!INPUT_TOKEN!" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo  [OK] ANTHROPIC_AUTH_TOKEN saved to system environment.
    ) else (
        setx ANTHROPIC_AUTH_TOKEN "!INPUT_TOKEN!" >nul 2>&1
        echo  [OK] ANTHROPIC_AUTH_TOKEN saved to user environment.
    )

    if not "!INPUT_URL!"=="" (
        setx /M ANTHROPIC_BASE_URL "!INPUT_URL!" >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            echo  [OK] ANTHROPIC_BASE_URL saved to system environment.
        ) else (
            setx ANTHROPIC_BASE_URL "!INPUT_URL!" >nul 2>&1
            echo  [OK] ANTHROPIC_BASE_URL saved to user environment.
        )
    )
    echo.
)

REM ============================================================
REM Step 2: Open parent directory in VS Code or Cursor
REM ============================================================

REM -- VS Code --
set "CODE_EXE="
if exist "%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe" set "CODE_EXE=%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"
if not defined CODE_EXE (
    if exist "%ProgramFiles%\Microsoft VS Code\Code.exe" set "CODE_EXE=%ProgramFiles%\Microsoft VS Code\Code.exe"
)
if not defined CODE_EXE (
    where code >nul 2>&1
    if !ERRORLEVEL! EQU 0 set "CODE_EXE=code"
)

if defined CODE_EXE (
    echo  Opening in VS Code: %PARENT_DIR%
    if "!CODE_EXE!"=="code" (
        call code "!PARENT_DIR!"
    ) else (
        start "" "!CODE_EXE!" "!PARENT_DIR!"
    )
    exit /b 0
)

REM -- Cursor --
set "CURSOR_EXE="
if exist "%LOCALAPPDATA%\Programs\cursor\Cursor.exe" set "CURSOR_EXE=%LOCALAPPDATA%\Programs\cursor\Cursor.exe"
if not defined CURSOR_EXE (
    where cursor >nul 2>&1
    if !ERRORLEVEL! EQU 0 set "CURSOR_EXE=cursor"
)

if defined CURSOR_EXE (
    echo  Opening in Cursor: %PARENT_DIR%
    if "!CURSOR_EXE!"=="cursor" (
        call cursor "!PARENT_DIR!"
    ) else (
        start "" "!CURSOR_EXE!" "!PARENT_DIR!"
    )
    exit /b 0
)

echo  [Warning] VS Code and Cursor not found.
echo  Please open manually: %PARENT_DIR%
pause
exit /b 0

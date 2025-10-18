@echo off
chcp 65001 > nul
echo ====================================
echo Git Empty Commit Tool
echo ====================================
echo.

set /p commit_message="Commit message: "

if "%commit_message%"=="" (
    echo ERROR: Commit message is empty.
    pause
    exit /b 1
)

echo.
echo Creating empty commit...
git commit --allow-empty -m "%commit_message%"

if %errorlevel% equ 0 (
    echo.
    echo Success: Empty commit created!
) else (
    echo.
    echo Error: Failed to create commit.
)

echo.
pause

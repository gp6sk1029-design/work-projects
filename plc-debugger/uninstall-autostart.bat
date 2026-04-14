@echo off
chcp 65001 > nul
echo ========================================
echo   PLC Craft AI 自動起動を解除します
echo ========================================
echo.

schtasks /delete /tn "PLC Craft AI" /f >nul 2>&1

if errorlevel 1 (
    echo タスクが見つかりませんでした（すでに解除済みかもしれません）。
) else (
    echo [OK] 自動起動を解除しました。
)
echo.
pause

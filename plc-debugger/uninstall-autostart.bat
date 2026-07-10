@echo off
chcp 65001 > nul
echo ========================================
echo   PLC Craft AI 自動起動を解除します
echo ========================================
echo.

:: スタートアップフォルダのショートカットを削除
set SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\PLC Craft AI (Auto).lnk
if exist "%SHORTCUT%" (
    del "%SHORTCUT%"
    echo [OK] スタートアップフォルダから削除しました。
) else (
    echo スタートアップ登録が見つかりませんでした（すでに解除済みかもしれません）。
)

:: 旧方式（タスクスケジューラ）の登録が残っていれば掃除
schtasks /delete /tn "PLC Craft AI" /f >nul 2>&1

echo.
pause

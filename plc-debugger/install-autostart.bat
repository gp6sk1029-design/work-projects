@echo off
chcp 65001 > nul
title PLC Craft AI - 自動起動設定

echo ========================================
echo   PLC Craft AI 自動起動セットアップ
echo ========================================
echo.
echo Windows ログイン時に自動起動するよう設定します。
echo.

:: タスクスケジューラに登録（ログオン時に最小化で起動）
schtasks /create /tn "PLC Craft AI" /tr "\"%~dp0start-silent.bat\"" /sc onlogon /rl highest /f >nul 2>&1

if errorlevel 1 (
    echo [ERROR] タスクの登録に失敗しました。
    echo 管理者として実行してください。
    echo （このファイルを右クリック → 管理者として実行）
    pause
    exit /b 1
)

echo [OK] タスクスケジューラに登録しました。
echo.
echo 次回 Windows ログイン時から自動で起動します。
echo.
echo 今すぐ起動しますか？ (Y/N)
set /p ans=
if /i "%ans%"=="Y" (
    start "" "%~dp0start-silent.bat"
    echo 起動しました。しばらくするとブラウザが開きます。
)

echo.
echo ※ 自動起動を解除したい場合は uninstall-autostart.bat を実行してください。
echo.
pause

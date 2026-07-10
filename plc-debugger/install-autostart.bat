@echo off
chcp 65001 > nul
title PLC Craft AI - 自動起動設定

echo ========================================
echo   PLC Craft AI 自動起動セットアップ
echo ========================================
echo.
echo Windows ログイン時に自動起動するよう設定します。
echo （スタートアップフォルダ方式・管理者権限は不要です）
echo.

:: スタートアップフォルダにショートカットを作成
:: ※タスクスケジューラ方式は管理者権限が必要で失敗するため使わない（2026-05-29確立の恒久対策）
set SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\PLC Craft AI (Auto).lnk

powershell -NoProfile -Command ^
  "$sh = New-Object -ComObject WScript.Shell;" ^
  "$lnk = $sh.CreateShortcut('%SHORTCUT%');" ^
  "$lnk.TargetPath = 'C:\WINDOWS\system32\wscript.exe';" ^
  "$lnk.Arguments = '\"%~dp0start-hidden.vbs\"';" ^
  "$lnk.WorkingDirectory = '%~dp0.';" ^
  "$lnk.Save()"

if errorlevel 1 (
    echo [ERROR] ショートカットの作成に失敗しました。
    pause
    exit /b 1
)

echo [OK] スタートアップフォルダに登録しました。
echo.
echo 次回 Windows ログイン時から自動で起動します。
echo.
echo 今すぐ起動しますか？ (Y/N)
set /p ans=
if /i "%ans%"=="Y" (
    wscript.exe "%~dp0start-hidden.vbs"
    echo 起動しました。http://localhost:3001 を開いてください。
)

echo.
echo ※ 自動起動を解除したい場合は uninstall-autostart.bat を実行してください。
echo.
pause

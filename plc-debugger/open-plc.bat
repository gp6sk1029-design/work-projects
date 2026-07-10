@echo off
chcp 65001 > nul
title PLC Craft AI - スマート起動

::
:: スマート起動（本番モード対応・ポート3001）
::   1. 既に起動済みならブラウザで開くだけ
::   2. 未起動なら start-hidden.vbs で非表示起動してからブラウザを開く
::

set ROOT=%~dp0

:: 本番ポート3001のヘルスチェック
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:3001/api/health' -UseBasicParsing -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    start "" "http://localhost:3001"
    exit /b 0
)

:: 未起動 → 非表示で本番起動
echo PLC Craft AI を起動中... 初回は20秒ほどかかります
wscript "%ROOT%start-hidden.vbs"

:: 起動を待ってブラウザを開く（最大30秒）
set /a count=0
:wait
ping -n 3 127.0.0.1 >nul
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:3001/api/health' -UseBasicParsing -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    start "" "http://localhost:3001"
    exit /b 0
)
set /a count+=1
if %count% lss 12 goto :wait
echo タイムアウト。server\boot.log を確認してください。
exit /b 1

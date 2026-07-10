@echo off
chcp 65001 > nul
title FP7 Diff - スマート起動

::
:: スマート起動（本番モード対応・ポート3002）
::

set ROOT=%~dp0

powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:3002/api/health' -UseBasicParsing -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    start "" "http://localhost:3002"
    exit /b 0
)

echo FP7 Diff を起動中... 初回は20秒ほどかかります
wscript "%ROOT%start-hidden.vbs"

set /a count=0
:wait
ping -n 3 127.0.0.1 >nul
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:3002/api/health' -UseBasicParsing -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    start "" "http://localhost:3002"
    exit /b 0
)
set /a count+=1
if %count% lss 12 goto :wait
echo タイムアウト。server\boot.log を確認してください。
exit /b 1

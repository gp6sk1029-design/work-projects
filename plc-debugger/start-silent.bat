@echo off
chcp 65001 > nul

:: バックグラウンドで静かに起動するスクリプト（タスクスケジューラ用）
:: ウィンドウを最小化して邪魔にならない

set ROOT=%~dp0

:: ポート競合クリーンアップ
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":3001 "') do taskkill /F /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":5173 "') do taskkill /F /PID %%p >nul 2>&1
timeout /t 1 /nobreak > nul

:: バックエンド起動（最小化）
start /min "PLC Craft AI - Backend" cmd /k "cd /d "%ROOT%server" && npx tsx src/index.ts"

:: バックエンド起動待機
:wait_backend
timeout /t 2 /nobreak > nul
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:3001/api/health' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 goto :wait_backend

:: フロントエンド起動（最小化）
start /min "PLC Craft AI - Frontend" cmd /k "cd /d "%ROOT%client" && npx vite --host"

:: フロントエンド起動待機
set /a count=0
:wait_frontend
timeout /t 2 /nobreak > nul
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:5173' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto :open_browser
set /a count+=1
if %count% lss 15 goto :wait_frontend

:open_browser
:: ブラウザを開く
start "" "http://localhost:5173"

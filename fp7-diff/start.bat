@echo off
chcp 65001 > nul
title FP7 Diff - 起動中

echo ========================================
echo   FP7 Diff 起動スクリプト
echo ========================================
echo.

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js が見つかりません。
    pause
    exit /b 1
)

if not exist "%~dp0server\.env" (
    echo [WARNING] server\.env が見つかりません。
    echo   GEMINI_API_KEY未設定だとAI解説が動作しません。
    echo.
)

:: ポート競合クリア
echo [0/3] ポート競合チェック中...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":3002 "') do taskkill /F /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":5174 "') do taskkill /F /PID %%p >nul 2>&1
timeout /t 1 /nobreak > nul

:: 依存自動インストール
if not exist "%~dp0server\node_modules" (
    echo [準備] server 依存パッケージをインストール中...
    cd /d "%~dp0server"
    call npm install
    cd /d "%~dp0"
)
if not exist "%~dp0client\node_modules" (
    echo [準備] client 依存パッケージをインストール中...
    cd /d "%~dp0client"
    call npm install
    cd /d "%~dp0"
)

echo [1/3] バックエンド起動中 (port 3002)...
start "FP7 Diff - Backend" cmd /k "cd /d "%~dp0server" && npx tsx src/index.ts"

echo [2/3] バックエンド待機中...
set /a count=0
:wait_backend
timeout /t 2 /nobreak > nul
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:3002/api/health' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo   バックエンド起動OK
    goto :backend_ready
)
set /a count+=1
if %count% lss 15 goto :wait_backend
echo   [WARNING] バックエンド応答なし

:backend_ready
echo [3/3] フロントエンド起動中 (port 5174)...
start "FP7 Diff - Frontend" cmd /k "cd /d "%~dp0client" && npx vite --host"

set /a count=0
:wait_frontend
timeout /t 2 /nobreak > nul
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:5174' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto :open
set /a count+=1
if %count% lss 10 goto :wait_frontend

:open
echo.
echo ブラウザを起動中...
timeout /t 1 /nobreak > nul
start "" "http://localhost:5174"

echo.
echo ========================================
echo   起動完了！  http://localhost:5174
echo ========================================
pause

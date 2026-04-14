@echo off
chcp 65001 > nul
title PLC Craft AI - 起動中

echo ========================================
echo   PLC Craft AI 起動スクリプト
echo ========================================
echo.

:: Node.js パスを確認
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js が見つかりません。
    echo   https://nodejs.org からインストールしてください。
    pause
    exit /b 1
)

:: .env ファイル確認
if not exist "%~dp0server\.env" (
    echo [ERROR] server\.env ファイルが見つかりません。
    echo.
    echo   以下の内容で server\.env を作成してください:
    echo   GEMINI_API_KEY=あなたのAPIキー
    echo   PORT=3001
    echo.
    pause
    exit /b 1
)

:: 既存プロセスをポートで終了（ポート競合を防ぐ）
echo [0/3] ポート競合チェック中...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":3001 "') do (
    taskkill /F /PID %%p >nul 2>&1
)
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":5173 "') do (
    taskkill /F /PID %%p >nul 2>&1
)
timeout /t 1 /nobreak > nul

:: バックエンドサーバーを起動
echo [1/3] バックエンドサーバー起動中 (port 3001)...
start "PLC Craft AI - Backend" cmd /k "cd /d "%~dp0server" && npx tsx src/index.ts"

:: バックエンドが起動するまで待機（最大30秒、PowerShellでヘルスチェック）
echo [2/3] バックエンド起動待機中...
set /a count=0
:wait_backend
timeout /t 2 /nobreak > nul
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:3001/api/health' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo   バックエンド起動OK!
    goto :backend_ready
)
set /a count+=1
if %count% lss 15 (
    if %count%==1  echo   少々お待ちください...
    if %count%==5  echo   まだ起動中...
    if %count%==10 echo   もう少し...
    goto :wait_backend
)
echo   [WARNING] バックエンドの応答がありません。起動に失敗した可能性があります。
echo   Backend ウィンドウでエラーを確認してください。
echo.

:backend_ready

:: フロントエンドを起動
echo [3/3] フロントエンド起動中 (port 5173)...
start "PLC Craft AI - Frontend" cmd /k "cd /d "%~dp0client" && npx vite --host"

:: フロントエンドが起動するまで待機（最大20秒）
echo   フロントエンド起動待機中...
set /a count=0
:wait_frontend
timeout /t 2 /nobreak > nul
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:5173' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo   フロントエンド起動OK!
    goto :frontend_ready
)
set /a count+=1
if %count% lss 10 (
    if %count%==1 echo   少々お待ちください...
    if %count%==5 echo   もう少し...
    goto :wait_frontend
)
echo   [WARNING] フロントエンドの応答がありません。

:frontend_ready

:: ブラウザを自動で開く
echo.
echo ブラウザを起動中...
timeout /t 1 /nobreak > nul
start "" "http://localhost:5173"

echo.
echo ========================================
echo   起動完了！
echo   http://localhost:5173
echo ========================================
echo.
echo このウィンドウは閉じても構いません。
echo サーバーを止めるには stop.bat を実行するか、
echo Backend / Frontend のウィンドウを閉じてください。
echo.
pause

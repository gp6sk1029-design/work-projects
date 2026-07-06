@echo off
chcp 65001 > nul
title 検図ツール - 起動中

echo ========================================
echo   検図ツール (drawing-checker)
echo ========================================
echo.

:: Node.js 確認
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js が見つかりません。
    echo   https://nodejs.org からインストールしてください。
    pause
    exit /b 1
)

:: Python 確認
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python が見つかりません。
    pause
    exit /b 1
)

:: Python依存関係の確認
python -c "import fitz, ezdxf" >nul 2>&1
if errorlevel 1 (
    echo [注意] Python依存関係が不足しています。インストールしますか？(Y/N)
    set /p INSTALL=
    if /i "%INSTALL%"=="Y" (
        python -m pip install -r "%~dp0requirements.txt"
    )
)

:: server 依存関係
if not exist "%~dp0server\node_modules" (
    echo [初回セットアップ] server 依存関係をインストール中...
    pushd "%~dp0server"
    call npm install
    popd
)

:: client 依存関係
if not exist "%~dp0client\node_modules" (
    echo [初回セットアップ] client 依存関係をインストール中...
    pushd "%~dp0client"
    call npm install
    popd
)

:: ポート競合チェック
echo [0/3] ポート競合チェック中...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":3001 "') do (
    taskkill /F /PID %%p >nul 2>&1
)
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":5174 "') do (
    taskkill /F /PID %%p >nul 2>&1
)
timeout /t 1 /nobreak > nul

:: バックエンド起動
echo [1/3] バックエンド起動中 (port 3001)...
start "検図ツール - Backend" cmd /k "cd /d "%~dp0server" && npx tsx src/index.ts"

:: 起動待機
echo [2/3] バックエンド起動待機中...
set /a count=0
:wait_backend
timeout /t 2 /nobreak > nul
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:3001/api/health' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto :backend_ready
set /a count+=1
if %count% lss 15 goto :wait_backend
echo   [WARNING] バックエンドの応答がありません。
:backend_ready
echo   バックエンド起動OK!

:: フロントエンド起動
echo [3/3] フロントエンド起動中 (port 5174)...
start "検図ツール - Frontend" cmd /k "cd /d "%~dp0client" && npx vite --host"

set /a count=0
:wait_frontend
timeout /t 2 /nobreak > nul
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:5174' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto :frontend_ready
set /a count+=1
if %count% lss 10 goto :wait_frontend
:frontend_ready

echo.
echo ブラウザを起動中...
timeout /t 1 /nobreak > nul
start "" "http://localhost:5174"

echo.
echo ========================================
echo   起動完了！  http://localhost:5174
echo ========================================
echo.
echo 停止するには stop.bat または各ウィンドウを閉じてください
pause

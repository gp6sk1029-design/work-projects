@echo off
chcp 65001 > nul
title Media Transcriber - 起動中

echo ========================================
echo   Media Transcriber 起動スクリプト
echo ========================================
echo.

set "APP_DIR=%~dp0"
set "PATH=C:\Program Files\nodejs;%PATH%"

:: FFmpeg存在チェック（警告のみ）
where ffmpeg >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [警告] FFmpegが見つかりません
    echo   一部機能が制限されます
    echo.
) else (
    echo [OK] FFmpeg検出
)

:: バックエンドサーバー起動
echo [1/2] バックエンドサーバー起動中 (port 3002)...
start "Media Transcriber - Backend" cmd /k "cd /d "%APP_DIR%server" && npx tsx src/index.ts"

timeout /t 4 /nobreak > nul

:: フロントエンド起動
echo [2/2] フロントエンド起動中 (port 5174)...
start "Media Transcriber - Frontend" cmd /k "cd /d "%APP_DIR%client" && npx vite --host"

timeout /t 5 /nobreak > nul

:: ブラウザを自動で開く
start http://localhost:5174

echo.
echo ========================================
echo   起動完了！
echo   ブラウザが自動で開きます
echo   http://localhost:5174
echo ========================================
echo.
echo このウィンドウは閉じても構いません。
echo サーバーを止めるには Backend/Frontend の
echo ウィンドウを閉じてください。
echo.
pause

@echo off
chcp 65001 > nul
title PLC Craft AI (本番モード)

::
:: 本番モード起動: Express単体でフロント込み配信（vite不要）
::   http://localhost:3001 で全機能アクセス可能
::   タスクスケジューラからログオン時に呼ばれる
::

set ROOT=%~dp0

:: ポート競合クリア（旧プロセスを掃除）
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":3001 "') do taskkill /F /PID %%p >nul 2>&1
:: 非対話環境でも安全な待機（timeout は標準入力なしで失敗するため ping を使用）
ping -n 2 127.0.0.1 >nul

:: 本番モードでExpress起動（ログは server/boot.log に残す）
cd /d "%ROOT%server"
set NODE_ENV=production
set PORT=3001
npx tsx src/index.ts >> "%ROOT%server\boot.log" 2>&1

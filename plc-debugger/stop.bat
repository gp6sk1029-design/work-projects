@echo off
chcp 65001 > nul
echo ========================================
echo   PLC Craft AI 停止中...
echo ========================================

:: ポート3001 (バックエンド) を停止
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":3001 "') do (
    taskkill /F /PID %%p >nul 2>&1
    echo   バックエンド (PID: %%p) 停止しました
)

:: ポート5173 (フロントエンド) を停止
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":5173 "') do (
    taskkill /F /PID %%p >nul 2>&1
    echo   フロントエンド (PID: %%p) 停止しました
)

echo.
echo 停止完了。
pause

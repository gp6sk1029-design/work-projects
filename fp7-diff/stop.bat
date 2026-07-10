@echo off
chcp 65001 > nul
echo FP7 Diff 停止中...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":3002 "') do taskkill /F /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":5174 "') do taskkill /F /PID %%p >nul 2>&1
echo 停止完了
timeout /t 2 /nobreak > nul

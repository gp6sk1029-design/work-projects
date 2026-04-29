@echo off
chcp 65001 > nul
echo 検図ツールを停止します...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":3001 "') do taskkill /F /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":5174 "') do taskkill /F /PID %%p >nul 2>&1
echo 停止しました。
timeout /t 2 /nobreak > nul

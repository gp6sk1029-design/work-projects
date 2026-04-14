@echo off
powershell -ExecutionPolicy Bypass -Command "& { $dir = Split-Path -Parent '%~f0'; Start-Process python -ArgumentList \"$dir\メール秘書.pyw\" -WorkingDirectory $dir }"

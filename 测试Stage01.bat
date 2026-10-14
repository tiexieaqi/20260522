@echo off
chcp 65001 >nul
cd /d "%~dp0"
python 程序\live_test_stage01.py
echo.
echo 测试结束。按任意键关闭窗口。
pause >nul

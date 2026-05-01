@echo off
chcp 65001 > nul
echo === md_yomikakikun build ===

set SCRIPT_DIR=%~dp0
set PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe

REM Clean previous build artifacts
if exist "%SCRIPT_DIR%build" (
    echo Cleaning build\...
    rmdir /s /q "%SCRIPT_DIR%build"
)
if exist "%SCRIPT_DIR%dist" (
    echo Cleaning dist\...
    rmdir /s /q "%SCRIPT_DIR%dist"
)

echo Running PyInstaller...
"%PYTHON%" -m PyInstaller --clean "%SCRIPT_DIR%md_yomikakikun.spec"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] PyInstaller failed.
    pause
    exit /b 1
)

echo.
echo Build complete: dist\md_yomikakikun\md_yomikakikun.exe
pause

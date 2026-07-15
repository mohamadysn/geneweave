@echo off
REM Build GeneWeave standalone binaries for Windows.
setlocal EnableExtensions

set "ROOT=%~dp0.."
cd /d "%ROOT%"

if "%PYTHON%"=="" (
  if exist "%ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
  ) else (
    set "PYTHON=python"
  )
)
if "%DIST_DIR%"=="" set "DIST_DIR=%ROOT%\dist"
if "%BUILD_DIR%"=="" set "BUILD_DIR=%ROOT%\build"

echo ==^> Installing build dependencies
"%PYTHON%" -m pip install -q -r requirements.txt -r requirements-build.txt
if errorlevel 1 exit /b 1

echo ==^> Cleaning previous build
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%DIST_DIR%\GeneWeave.exe" del /f /q "%DIST_DIR%\GeneWeave.exe"
if exist "%DIST_DIR%\geneweave-cli.exe" del /f /q "%DIST_DIR%\geneweave-cli.exe"
if exist "%DIST_DIR%\geneweave-viewer.exe" del /f /q "%DIST_DIR%\geneweave-viewer.exe"
del /f /q "%DIST_DIR%\GeneWeave-*-windows.zip" 2>nul

echo ==^> Running PyInstaller
"%PYTHON%" -m PyInstaller --noconfirm --clean --distpath "%DIST_DIR%" --workpath "%BUILD_DIR%" packaging\geneweave.spec
if errorlevel 1 exit /b 1

for /f "delims=" %%V in ('"%PYTHON%" -c "from annotation.config import VERSION; print(VERSION)"') do set "VERSION=%%V"
set "ARCHIVE=%DIST_DIR%\GeneWeave-%VERSION%-windows.zip"

echo ==^> Packaging %ARCHIVE%
powershell -NoProfile -Command "Compress-Archive -Path '%DIST_DIR%\GeneWeave.exe','%DIST_DIR%\geneweave-cli.exe','%DIST_DIR%\geneweave-viewer.exe' -DestinationPath '%ARCHIVE%' -Force"
if errorlevel 1 exit /b 1

echo.
echo Build complete.
echo   GUI    : %DIST_DIR%\GeneWeave.exe
echo   CLI    : %DIST_DIR%\geneweave-cli.exe
echo   Viewer : %DIST_DIR%\geneweave-viewer.exe
echo   Archive: %ARCHIVE%

endlocal

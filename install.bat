@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   FreeCAD [Ring] Workbench Auto Installer (v1-1)
echo ===================================================
echo.

:: ワークベンチのフォルダ名を指定
set "WORKBENCH_NAME=Ring"

:: ZIPのまま実行されていないかチェック
echo "%~dp0" | findstr /i "AppData\Local\Temp" > nul
if %errorlevel% equ 0 (
    echo [ERROR] Please UNZIP the file before running this batch!
    echo.
    goto END
)

:: インストール元フォルダの確認
set "SOURCE_DIR=%~dp0%WORKBENCH_NAME%"
if not exist "%SOURCE_DIR%" (
    echo [ERROR] Folder "%WORKBENCH_NAME%" not found.
    echo Please make sure this batch file and the "%WORKBENCH_NAME%" folder are in the same place.
    echo.
    goto END
)

:: FreeCAD 1.1 用のインストール先
set "TARGET_DIR=%APPDATA%\FreeCAD\v1-1\Mod\%WORKBENCH_NAME%"
set "PARENT_DIR=%APPDATA%\FreeCAD\v1-1\Mod"

echo Installing to FreeCAD Mod folder...
echo Destination: %TARGET_DIR%
echo.

:: 親フォルダが存在しない場合は作成
if not exist "%PARENT_DIR%" (
    mkdir "%PARENT_DIR%"
)

:: 古いバージョンが存在する場合は削除
if exist "%TARGET_DIR%" (
    echo Old version found. Updating...
    rmdir /s /q "%TARGET_DIR%"
)

:: ファイルのコピー実行
xcopy "%SOURCE_DIR%" "%TARGET_DIR%" /E /I /H /Y > nul

if %errorlevel% equ 0 (
    echo ---------------------------------------------------
    echo SUCCESS: Installation Complete!
    echo Please restart FreeCAD to use your "Ring" workbench.
    echo ---------------------------------------------------
) else (
    echo [ERROR] Installation failed.
)

:END
echo.
pause
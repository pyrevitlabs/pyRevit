@echo off
echo ============================================================
echo pyRevit Windows 11 Configuration Test
echo ============================================================
echo.

echo Testing system information...
echo Platform: %OS%
echo Computer: %COMPUTERNAME%
echo User: %USERNAME%
echo.

echo Testing environment variables...
echo APPDATA: %APPDATA%
echo LOCALAPPDATA: %LOCALAPPDATA%
echo USERPROFILE: %USERPROFILE%
echo.

echo Testing directory access...
if exist "%APPDATA%" (
    echo [PASS] APPDATA directory exists
) else (
    echo [FAIL] APPDATA directory does not exist
)

if exist "%LOCALAPPDATA%" (
    echo [PASS] LOCALAPPDATA directory exists
) else (
    echo [FAIL] LOCALAPPDATA directory does not exist
)

echo.
echo Testing pyRevit directory creation...
set PYREVIT_TEST_DIR=%APPDATA%\pyRevit_test
set CONFIG_TEST_FILE=%PYREVIT_TEST_DIR%\pyRevit_config.ini

rem Clean up if exists
if exist "%PYREVIT_TEST_DIR%" rmdir /s /q "%PYREVIT_TEST_DIR%"

rem Create pyRevit test directory
mkdir "%PYREVIT_TEST_DIR%" 2>nul
if exist "%PYREVIT_TEST_DIR%" (
    echo [PASS] pyRevit test directory created successfully
) else (
    echo [FAIL] Could not create pyRevit test directory
    goto :error
)

echo.
echo Testing configuration file creation...
echo # pyRevit Configuration File > "%CONFIG_TEST_FILE%"
echo # Created by manual test script >> "%CONFIG_TEST_FILE%"
echo. >> "%CONFIG_TEST_FILE%"
echo [core] >> "%CONFIG_TEST_FILE%"
echo # Core pyRevit settings >> "%CONFIG_TEST_FILE%"
echo check_updates = true >> "%CONFIG_TEST_FILE%"
echo. >> "%CONFIG_TEST_FILE%"
echo [extensions] >> "%CONFIG_TEST_FILE%"
echo # Extension settings >> "%CONFIG_TEST_FILE%"
echo. >> "%CONFIG_TEST_FILE%"
echo [user] >> "%CONFIG_TEST_FILE%"
echo # User-specific settings >> "%CONFIG_TEST_FILE%"

if exist "%CONFIG_TEST_FILE%" (
    echo [PASS] Configuration file created successfully
) else (
    echo [FAIL] Could not create configuration file
    goto :error
)

echo.
echo Testing file modification...
echo. >> "%CONFIG_TEST_FILE%"
echo [test_section] >> "%CONFIG_TEST_FILE%"
echo test_setting = test_value >> "%CONFIG_TEST_FILE%"
echo modified_timestamp = %date% %time% >> "%CONFIG_TEST_FILE%"

findstr "test_section" "%CONFIG_TEST_FILE%" >nul
if %errorlevel% equ 0 (
    echo [PASS] Configuration file modification successful
) else (
    echo [FAIL] Configuration file modification failed
    goto :error
)

echo.
echo Testing file reading...
echo Configuration file contents:
echo ----------------------------------------
type "%CONFIG_TEST_FILE%"
echo ----------------------------------------

echo.
echo Testing alternative locations...
set ALT_DIR1=%LOCALAPPDATA%\pyRevit_test
set ALT_DIR2=%USERPROFILE%\.pyrevit_test

mkdir "%ALT_DIR1%" 2>nul
if exist "%ALT_DIR1%" (
    echo [PASS] Alternative location 1 (LOCALAPPDATA) accessible
    rmdir /s /q "%ALT_DIR1%"
) else (
    echo [WARN] Alternative location 1 (LOCALAPPDATA) not accessible
)

mkdir "%ALT_DIR2%" 2>nul
if exist "%ALT_DIR2%" (
    echo [PASS] Alternative location 2 (USERPROFILE) accessible
    rmdir /s /q "%ALT_DIR2%"
) else (
    echo [WARN] Alternative location 2 (USERPROFILE) not accessible
)

echo.
echo Testing Windows version...
ver | findstr "10.0" >nul
if %errorlevel% equ 0 (
    echo [INFO] Windows 10/11 detected
    for /f "tokens=3" %%i in ('ver') do set WIN_VER=%%i
    echo [INFO] Version: %WIN_VER%
) else (
    echo [INFO] Windows version could not be determined
)

echo.
echo Cleanup...
if exist "%PYREVIT_TEST_DIR%" (
    rmdir /s /q "%PYREVIT_TEST_DIR%"
    echo [PASS] Cleanup completed
)

echo.
echo ============================================================
echo TEST SUMMARY
echo ============================================================
echo [PASS] All core functionality tests passed
echo [INFO] Configuration file creation and modification works
echo [INFO] pyRevit should be able to save settings on this system
echo.
echo If pyRevit still has issues:
echo 1. Run as Administrator
echo 2. Check Windows Security settings
echo 3. Verify antivirus exclusions
echo 4. Check Controlled Folder Access settings
echo ============================================================
goto :end

:error
echo.
echo ============================================================
echo TEST FAILED
echo ============================================================
echo [ERROR] Configuration file operations failed
echo [ERROR] This indicates Windows 11 compatibility issues
echo.
echo Recommended actions:
echo 1. Run this script as Administrator
echo 2. Check Windows Security ^> Virus ^& threat protection
echo 3. Disable Controlled Folder Access temporarily
echo 4. Add pyRevit to antivirus exclusions
echo 5. Check folder permissions in %APPDATA%
echo ============================================================

:end
pause

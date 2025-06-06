# PowerShell script to fix pyRevit configuration issues on Windows 11
param(
    [switch]$Diagnose,
    [switch]$Fix
)

function Write-Header {
    param([string]$Title)
    Write-Host "`n$('=' * 60)" -ForegroundColor Cyan
    Write-Host $Title -ForegroundColor Cyan
    Write-Host "$('=' * 60)" -ForegroundColor Cyan
}

function Test-WindowsVersion {
    Write-Header "Windows Version Check"
    
    $version = [System.Environment]::OSVersion.Version
    $build = $version.Build
    
    Write-Host "Windows Version: $($version.ToString())" -ForegroundColor White
    Write-Host "Build Number: $build" -ForegroundColor White
    
    $isWindows11 = $build -ge 22000
    if ($isWindows11) {
        Write-Host "✓ Windows 11 detected" -ForegroundColor Green
    } else {
        Write-Host "ℹ Windows 10 or earlier detected" -ForegroundColor Yellow
    }
    
    return $isWindows11
}

function Test-DirectoryAccess {
    param([string]$Path)
    
    try {
        if (-not (Test-Path $Path)) {
            New-Item -Path $Path -ItemType Directory -Force | Out-Null
        }
        
        $testFile = Join-Path $Path "test_permissions.tmp"
        "test" | Out-File -FilePath $testFile -Force
        Remove-Item $testFile -Force
        
        return $true
    }
    catch {
        return $false
    }
}

function Get-PyRevitPaths {
    Write-Header "pyRevit Path Analysis"
    
    $paths = @{
        "AppData" = $env:APPDATA
        "LocalAppData" = $env:LOCALAPPDATA
        "UserProfile" = $env:USERPROFILE
        "PyRevitAppData" = Join-Path $env:APPDATA "pyRevit"
        "PyRevitLocalAppData" = Join-Path $env:LOCALAPPDATA "pyRevit"
        "PyRevitUserProfile" = Join-Path $env:USERPROFILE ".pyrevit"
    }
    
    foreach ($name in $paths.Keys) {
        $path = $paths[$name]
        Write-Host "$name`: $path" -ForegroundColor White
        
        if (Test-Path $path) {
            $hasAccess = Test-DirectoryAccess $path
            if ($hasAccess) {
                Write-Host "  ✓ Accessible and writable" -ForegroundColor Green
            } else {
                Write-Host "  ✗ Permission denied" -ForegroundColor Red
            }
        } else {
            Write-Host "  ⚠ Does not exist" -ForegroundColor Yellow
        }
    }
    
    return $paths
}

function Test-ConfigFile {
    param([string]$ConfigPath)
    
    Write-Header "Configuration File Test"
    
    Write-Host "Testing config file: $ConfigPath" -ForegroundColor White
    
    if (Test-Path $ConfigPath) {
        Write-Host "✓ Config file exists" -ForegroundColor Green
        
        try {
            $content = Get-Content $ConfigPath -Raw
            Write-Host "✓ Config file is readable" -ForegroundColor Green
            return $true
        }
        catch {
            Write-Host "✗ Config file access error: $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
    } else {
        Write-Host "⚠ Config file does not exist" -ForegroundColor Yellow
        return $false
    }
}

function Create-ConfigFile {
    param([string]$ConfigPath)
    
    Write-Header "Creating Configuration File"
    
    $configDir = Split-Path $ConfigPath -Parent
    
    try {
        if (-not (Test-Path $configDir)) {
            Write-Host "Creating directory: $configDir" -ForegroundColor Yellow
            New-Item -Path $configDir -ItemType Directory -Force | Out-Null
        }
        
        $configContent = @"
# pyRevit Configuration File
# Created by Windows 11 compatibility script
# $(Get-Date)

[core]
# Core pyRevit settings

[extensions]
# Extension settings

[user]
# User-specific settings

"@
        
        Write-Host "Creating config file: $ConfigPath" -ForegroundColor Yellow
        $configContent | Out-File -FilePath $ConfigPath -Force -Encoding UTF8
        
        if (Test-Path $ConfigPath) {
            Write-Host "✓ Config file created successfully" -ForegroundColor Green
            return $true
        } else {
            Write-Host "✗ Failed to create config file" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "✗ Error creating config file: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Main {
    Write-Host "pyRevit Windows 11 Configuration Fix Tool" -ForegroundColor Cyan
    Write-Host "Version 1.0" -ForegroundColor Gray
    
    $isWindows11 = Test-WindowsVersion
    $paths = Get-PyRevitPaths
    
    $configPath = Join-Path $paths["PyRevitAppData"] "pyRevit_config.ini"
    
    if ($Diagnose -or (-not $Fix)) {
        Write-Header "Diagnosis Results"
        
        $configExists = Test-ConfigFile $configPath
        
        if (-not $configExists) {
            Write-Host "`nRecommendations:" -ForegroundColor Yellow
            Write-Host "1. Run this script with -Fix parameter" -ForegroundColor White
            Write-Host "2. If that fails, run as Administrator" -ForegroundColor White
            Write-Host "3. Check Windows Security settings" -ForegroundColor White
        }
    }
    
    if ($Fix) {
        Write-Header "Applying Fixes"
        
        $success = Create-ConfigFile $configPath
        
        if (-not $success) {
            Write-Host "Primary location failed, trying alternatives..." -ForegroundColor Yellow
            
            $altConfigPath = Join-Path $paths["PyRevitLocalAppData"] "pyRevit_config.ini"
            $success = Create-ConfigFile $altConfigPath
            
            if (-not $success) {
                $altConfigPath = Join-Path $paths["PyRevitUserProfile"] "pyRevit_config.ini"
                $success = Create-ConfigFile $altConfigPath
            }
            
            if ($success) {
                Write-Host "`nAlternative config file created at: $altConfigPath" -ForegroundColor Green
                Write-Host "You may need to copy this to: $configPath" -ForegroundColor Yellow
            }
        }
        
        if ($success) {
            Write-Host "`n✓ Configuration fix completed successfully!" -ForegroundColor Green
        } else {
            Write-Host "`n✗ Configuration fix failed. Try running as Administrator." -ForegroundColor Red
        }
    }
    
    Write-Header "Summary"
    Write-Host "For more help, visit: https://github.com/pyrevitlabs/pyRevit/issues" -ForegroundColor Cyan
}

# Run the main function
Main

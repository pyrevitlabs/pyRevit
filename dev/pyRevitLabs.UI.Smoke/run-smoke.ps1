$ErrorActionPreference = 'Stop'

$root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$clientProject = Join-Path $root 'dev\pyRevitLabs.UI.Client\pyRevitLabs.UI.Client.csproj'
$hostProject = Join-Path $root 'dev\pyRevitLabs.UI.Host\pyRevitLabs.UI.Host.csproj'
$probeProject = Join-Path $root 'dev\pyRevitLabs.UI.Probe\pyRevitLabs.UI.Probe.csproj'
$loaderProjects = @(
    @{ Name = '342'; Path = Join-Path $root 'dev\pyRevitLoader\pyRevitLoader.342\pyRevitLoader.342.csproj' },
    @{ Name = '2712PR'; Path = Join-Path $root 'dev\pyRevitLoader\pyRevitLoader.2712PR\pyRevitLoader.2712PR.csproj' }
)
$hostDll = Join-Path $root 'dev\pyRevitLabs.UI.Host\bin\Release\net10.0\pyrevit-ui-host.dll'
$deployedHostDll = Join-Path $root 'bin\ui-host\pyrevit-ui-host.dll'
$deployedHostRuntimeConfig = Join-Path $root 'bin\ui-host\pyrevit-ui-host.runtimeconfig.json'
$probeDll = Join-Path $root 'dev\pyRevitLabs.UI.Probe\bin\Release\net10.0-windows\pyrevit-ui-probe.dll'
$pipeName = "pyrevit-ui-poc-$PID-$([Guid]::NewGuid().ToString('N'))"
$logPath = Join-Path $env:TEMP "pyrevit-ui-host-$PID.log"

Write-Host '[UI-SMOKE] building multi-target client'
dotnet build $clientProject -c Release
if ($LASTEXITCODE -ne 0) { throw 'Client build failed.' }

Write-Host '[UI-SMOKE] building host'
dotnet build $hostProject -c Release
if ($LASTEXITCODE -ne 0) { throw 'Host build failed.' }

Write-Host '[UI-SMOKE] building probe'
dotnet build $probeProject -c Release
if ($LASTEXITCODE -ne 0) { throw 'Probe build failed.' }

if (-not (Test-Path $hostDll)) { throw "Host DLL not found: $hostDll" }
if (-not (Test-Path $deployedHostDll)) { throw "Deployed host DLL not found: $deployedHostDll" }
if (-not (Test-Path $deployedHostRuntimeConfig)) { throw "Deployed host runtime config not found: $deployedHostRuntimeConfig" }
if (-not (Test-Path $probeDll)) { throw "Probe DLL not found: $probeDll" }

$loaderTargets = @(
    @{ Year = 2021; Framework = 'net48' },
    @{ Year = 2022; Framework = 'net48' },
    @{ Year = 2023; Framework = 'net48' },
    @{ Year = 2024; Framework = 'net48' },
    @{ Year = 2025; Framework = 'net8.0-windows' },
    @{ Year = 2026; Framework = 'net10.0-windows' },
    @{ Year = 2027; Framework = 'net10.0-windows' }
)

foreach ($loader in $loaderProjects) {
    foreach ($target in $loaderTargets) {
        Write-Host "[UI-SMOKE] building loader $($loader.Name) for Revit $($target.Year) / $($target.Framework)"
        dotnet build $loader.Path -c Release `
            -p:TargetFrameworks=$($target.Framework) `
            -p:RevitVersion=$($target.Year) `
            -p:SkipPyRevitDeploy=true
        if ($LASTEXITCODE -ne 0) {
            throw "Loader $($loader.Name) Revit $($target.Year) build failed."
        }
    }
}

Write-Host "[UI-SMOKE] running launcher probe pipe=$pipeName log=$logPath"
$probeOutput = & dotnet $probeDll --host $hostDll --pipe $pipeName --log $logPath 2>&1
$probeExitCode = $LASTEXITCODE
$probeOutput | ForEach-Object { Write-Host $_ }

if ($probeExitCode -ne 0) { throw "Probe failed with exit code $probeExitCode." }
if (($probeOutput -join "`n") -notmatch '\[UI-PROBE\] PASS') { throw 'Probe did not report PASS.' }

if (($probeOutput -join "`n") -notmatch 'hostPid=(\d+)') { throw 'Probe did not report the host process id.' }
$hostProcessId = [int]$Matches[1]
Start-Sleep -Milliseconds 200
if (Get-Process -Id $hostProcessId -ErrorAction SilentlyContinue) {
    throw "Host process $hostProcessId is still running after the client session was disposed."
}

if (-not (Test-Path $logPath)) { throw 'Host log was not created.' }
$hostLog = Get-Content $logPath
$hostLog | ForEach-Object { Write-Host $_ }

$requiredPatterns = @(
    'starting host',
    'client connected',
    'hello client=pyrevit-ui-probe',
    'method=host.info',
    'sent type=response'
)

foreach ($pattern in $requiredPatterns) {
    if (($hostLog -join "`n") -notmatch [Regex]::Escape($pattern)) {
        throw "Host log is missing required pattern: $pattern"
    }
}

$watchPipeName = "pyrevit-ui-parent-watch-$PID-$([Guid]::NewGuid().ToString('N'))"
$watchLogPath = Join-Path $env:TEMP "pyrevit-ui-parent-watch-$PID.log"
$parentProcess = $null
$watchHostProcess = $null
try {
    Write-Host '[UI-SMOKE] verifying parent process watchdog'
    $parentProcess = Start-Process powershell `
        -ArgumentList @('-NoProfile', '-Command', 'Start-Sleep -Seconds 60') `
        -PassThru -NoNewWindow
    $watchHostProcess = Start-Process dotnet `
        -ArgumentList @($hostDll, '--pipe', $watchPipeName, '--log', $watchLogPath, '--parent-pid', $parentProcess.Id) `
        -PassThru -NoNewWindow

    Start-Sleep -Milliseconds 500
    if ($watchHostProcess.HasExited) { throw 'Parent-watch host exited before its parent.' }

    Stop-Process -Id $parentProcess.Id -Force
    $parentProcess.WaitForExit()

    $deadline = (Get-Date).AddSeconds(5)
    while (-not $watchHostProcess.HasExited -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 100
        $watchHostProcess.Refresh()
    }

    if (-not $watchHostProcess.HasExited) {
        throw "Parent-watch host $($watchHostProcess.Id) did not stop after parent exit."
    }

    $watchLog = Get-Content $watchLogPath
    $watchLog | ForEach-Object { Write-Host $_ }
    if (($watchLog -join "`n") -notmatch [Regex]::Escape("parent exited pid=$($parentProcess.Id)")) {
        throw 'Parent-watch host did not log the parent exit.'
    }
}
finally {
    if ($parentProcess -and -not $parentProcess.HasExited) { Stop-Process -Id $parentProcess.Id -Force }
    if ($watchHostProcess -and -not $watchHostProcess.HasExited) { Stop-Process -Id $watchHostProcess.Id -Force }
}

Write-Host '[UI-SMOKE] PASS'

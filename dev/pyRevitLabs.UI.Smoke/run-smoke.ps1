$ErrorActionPreference = 'Stop'

$root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$clientProject = Join-Path $root 'dev\pyRevitLabs.UI.Client\pyRevitLabs.UI.Client.csproj'
$hostProject = Join-Path $root 'dev\pyRevitLabs.UI.Host\pyRevitLabs.UI.Host.csproj'
$probeProject = Join-Path $root 'dev\pyRevitLabs.UI.Probe\pyRevitLabs.UI.Probe.csproj'
$loaderProject = Join-Path $root 'dev\pyRevitLoader\pyRevitLoader.342\pyRevitLoader.342.csproj'
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

Write-Host '[UI-SMOKE] building Revit 2024 loader integration'
dotnet build $loaderProject -c Release -f net48 -p:RevitVersion=2024 -p:SkipPyRevitDeploy=true
if ($LASTEXITCODE -ne 0) { throw 'Revit 2024 loader build failed.' }

Write-Host '[UI-SMOKE] building Revit 2026 loader integration'
dotnet build $loaderProject -c Release -f net8.0-windows -p:RevitVersion=2026 -p:SkipPyRevitDeploy=true
if ($LASTEXITCODE -ne 0) { throw 'Revit 2026 loader build failed.' }

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

Write-Host '[UI-SMOKE] PASS'

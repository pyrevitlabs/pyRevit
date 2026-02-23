# NUKE bootstrap for pyRevit build
[CmdletBinding()]
Param(
    [Parameter(Position = 0, Mandatory = $false, ValueFromRemainingArguments = $true)]
    [string[]]$BuildArguments
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path $MyInvocation.MyCommand.Path -Parent

$BuildProjectFile = Join-Path $PSScriptRoot "build\build.csproj"
$env:DOTNET_CLI_TELEMETRY_OPTOUT = 1
$env:DOTNET_NOLOGO = 1
$env:NUKE_TELEMETRY_OPTOUT = 1

if (!(Test-Path $BuildProjectFile)) {
    Write-Error "Build project not found: $BuildProjectFile"
    exit 1
}

& dotnet build $BuildProjectFile /nodeReuse:false /p:UseSharedCompilation=false -nologo -clp:NoSummary
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& dotnet run --project $BuildProjectFile --no-build -- $BuildArguments
exit $LASTEXITCODE

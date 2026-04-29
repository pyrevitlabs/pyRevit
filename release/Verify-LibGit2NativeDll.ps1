# Verifies repo bin\ contains exactly one LibGit2Sharp native DLL (git2-*.dll).
# Run after `pipenv run pyrevit build products` or a full dotnet build that populates bin\.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$binDir = Join-Path $repoRoot 'bin'
if (-not (Test-Path -LiteralPath $binDir)) {
    throw "Missing directory: $binDir"
}
$git2 = @(Get-ChildItem -LiteralPath $binDir -Filter 'git2-*.dll' -File -ErrorAction SilentlyContinue)
if ($git2.Count -eq 0) {
    throw "Expected exactly one git2-*.dll in $binDir (LibGit2Sharp native). Found none. Ensure pyRevitLabs.Common DeployDependencies runs and copies natives to bin\."
}
if ($git2.Count -gt 1) {
    $names = ($git2 | ForEach-Object { $_.Name }) -join ', '
    throw "Expected exactly one git2-*.dll in $binDir. Found: $names"
}
Write-Host "LibGit2 native OK: $($git2[0].Name)"

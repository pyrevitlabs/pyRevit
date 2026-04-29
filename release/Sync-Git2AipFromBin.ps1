# Updates Advanced Installer .aip File/Component rows for the LibGit2 native DLL to match bin\git2-*.dll.
# Run after upgrading LibGit2Sharp or when AIP SourcePath no longer matches the built native name.
# Usage: pwsh -File release/Sync-Git2AipFromBin.ps1
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$binDir = Join-Path $repoRoot 'bin'
$git2 = @(Get-ChildItem -LiteralPath $binDir -Filter 'git2-*.dll' -File -ErrorAction SilentlyContinue)
if ($git2.Count -ne 1) {
    throw "Expected exactly one git2-*.dll in $binDir; found $($git2.Count)."
}
$newDll = $git2[0].Name
if ($newDll -notmatch '^git2-([0-9a-f]+)\.dll$') {
    throw "Unexpected native DLL name: $newDll"
}
$hex = $Matches[1]
$newComp = "git2$hex.dll"
$aipFiles = @(
    (Join-Path $PSScriptRoot 'pyrevit-cli.aip'),
    (Join-Path $PSScriptRoot 'pyrevit.aip')
)
foreach ($path in $aipFiles) {
    if (-not (Test-Path -LiteralPath $path)) { continue }
    $c = [System.IO.File]::ReadAllText($path)
    $c = [regex]::Replace($c, 'Component="git2[0-9a-f]+\.dll"', "Component=`"$newComp`"")
    $c = [regex]::Replace($c, 'KeyPath="git2[0-9a-f]+\.dll"', "KeyPath=`"$newComp`"")
    $c = [regex]::Replace($c, 'File="git2[0-9a-f]+\.dll"', "File=`"$newComp`"")
    $c = [regex]::Replace($c, 'Component_="git2[0-9a-f]+\.dll"', "Component_=`"$newComp`"")
    # Match either ..\bin\ or ..\\bin\\ (normalize to single backslashes per other rows)
    $c = [regex]::Replace($c, 'SourcePath="\.\.(?:\\)+bin(?:\\)+git2-[0-9a-f]+\.dll"', ('SourcePath="..\bin\{0}"' -f $newDll))
    $c = [regex]::Replace($c, 'FileName="([^|]*\|)git2-[0-9a-f]+\.dll"', "FileName=`"`$1$newDll`"")
    [System.IO.File]::WriteAllText($path, $c)
    Write-Host "Updated $path for $newDll"
}

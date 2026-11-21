$ErrorActionPreference = 'Stop'

$packageArgs = @{
  packageName    = $env:ChocolateyPackageName
  softwareName   = 'pyRevit version*'
  fileType       = 'exe'
  silentArgs     = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
  validExitCodes = @(0, 3010, 1605, 1614, 1641)
}

[array]$key = @(Get-UninstallRegistryKey -SoftwareName $packageArgs['softwareName']) |
  Where-Object { $_.PSPath -like '*HKEY_LOCAL_MACHINE*' }

if ($key.Count -eq 1) {
  $packageArgs['file'] = "$($key[0].UninstallString)"
  Uninstall-ChocolateyPackage @packageArgs
} elseif ($key.Count -eq 0) {
  Write-Warning "$($packageArgs['packageName']) has already been uninstalled by other means."
} else {
  $matched = ($key | ForEach-Object { "- $($_.DisplayName)" }) -join [Environment]::NewLine
  throw "$($key.Count) machine-wide installs match $($packageArgs['softwareName']), so none was uninstalled to prevent accidental data loss:$([Environment]::NewLine)$matched"
}

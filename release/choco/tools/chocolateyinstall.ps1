
$ErrorActionPreference = 'Stop';

$toolsDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$url64      = 'https://github.com/pyrevitlabs/pyRevit/releases/download/v6.1.0.26047%2B2255/pyRevit_CLI_6.1.0.26047_admin_signed.exe'

$packageArgs = @{
  packageName   = $env:ChocolateyPackageName
  unzipLocation = $toolsDir
  fileType      = 'exe'
  url64bit      = $url64

  softwareName  = 'pyrevit-cli*'

  checksum64    = 'A59DBF2FC5A68E5E3E0C1B60017C9027B313FCBB4F01B6C3F9D56AF82AB1E729'
  checksumType64= 'sha256'

  silentArgs    = "/VERYSILENT"
  validExitCodes= @(0, 3010, 1641)
}

Install-ChocolateyPackage @packageArgs










    









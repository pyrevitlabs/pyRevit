
$ErrorActionPreference = 'Stop';

$toolsDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$url64      = 'https://github.com/pyrevitlabs/pyRevit/releases/download/v5.0.1.25051%2B1239/pyRevit_CLI_5.0.1.25051_admin_signed.exe'

$packageArgs = @{
  packageName   = $env:ChocolateyPackageName
  unzipLocation = $toolsDir
  fileType      = 'exe'
  url64bit      = $url64

  softwareName  = 'pyrevit-cli*'

  checksum64    = '70AEF2EA6303106C54B2F8B321883F750D2D4C824F4C63D4D5AAED34C8D858BF'
  checksumType64= 'sha256'

  silentArgs    = "/VERYSILENT"
  validExitCodes= @(0, 3010, 1641)
}

Install-ChocolateyPackage @packageArgs










    









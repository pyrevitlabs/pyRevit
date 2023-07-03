
$ErrorActionPreference = 'Stop';

$toolsDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$url64      = 'https://github.com/eirannejad/pyRevit/releases/download/v4.8.13.23182/pyRevit_CLI_4.8.13.23182_admin_signed.exe'

$packageArgs = @{
  packageName   = $env:ChocolateyPackageName
  unzipLocation = $toolsDir
  fileType      = 'exe'
  url64bit      = $url64

  softwareName  = 'pyrevit-cli*'

  checksum64    = '3F72393F0F8E3511DD751617500304261BD6BDF813B6458E6BCE7A8F3AFB435D'
  checksumType64= 'sha256'

  silentArgs    = "/VERYSILENT"
  validExitCodes= @(0, 3010, 1641)
}

Install-ChocolateyPackage @packageArgs










    









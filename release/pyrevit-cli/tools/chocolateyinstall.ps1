
$ErrorActionPreference = 'Stop';

$toolsDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$url64      = 'https://github.com/eirannejad/pyRevit/releases/download/cli-v0.9.0.0/pyRevit.CLI_0.9.0.0_signed.exe'

$packageArgs = @{
  packageName   = $env:ChocolateyPackageName
  unzipLocation = $toolsDir
  fileType      = 'exe'
  url           = $url
  url64bit      = $url64

  softwareName  = 'pyrevit-cli*'

  checksum      = '0655648B5698FC2B9B22B650CC411AF07302A295E9C0C617B143A13447D689E3'
  checksumType  = 'sha256'
  checksum64    = '0655648B5698FC2B9B22B650CC411AF07302A295E9C0C617B143A13447D689E3'
  checksumType64= 'sha256'

  silentArgs    = "/qn"
  validExitCodes= @(0, 3010, 1641)
}

Install-ChocolateyPackage @packageArgs










    









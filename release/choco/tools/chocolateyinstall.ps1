
$ErrorActionPreference = 'Stop';

$toolsDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$url64      = 'https://github.com/eirannejad/pyRevit/releases/download/v4.8.9.21361%2B0320/pyRevit_CLI_4.8.9.21361+0320_admin_signed.exe'

$packageArgs = @{
  packageName   = $env:ChocolateyPackageName
  unzipLocation = $toolsDir
  fileType      = 'exe'
  url           = $url
  url64bit      = $url64

  softwareName  = 'pyrevit-cli*'

  checksum      = '7ae3487a95f0859db33cceae395b0c51afe644cf88dc8d1366db1f608cbf558f'
  checksumType  = 'sha256'
  checksum64    = '7ae3487a95f0859db33cceae395b0c51afe644cf88dc8d1366db1f608cbf558f'
  checksumType64= 'sha256'

  silentArgs    = "/VERYSILENT"
  validExitCodes= @(0, 3010, 1641)
}

Install-ChocolateyPackage @packageArgs










    









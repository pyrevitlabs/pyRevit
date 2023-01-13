
$ErrorActionPreference = 'Stop';

$toolsDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$url64      = 'https://github.com/eirannejad/pyRevit/releases/download/v4.8.12.22247%2B0031/pyRevit_CLI_4.8.12.22247_admin_signed.exe'

$packageArgs = @{
  packageName   = $env:ChocolateyPackageName
  unzipLocation = $toolsDir
  fileType      = 'exe'
  url64bit      = $url64

  softwareName  = 'pyrevit-cli*'

  checksum64    = 'ADA638CED8500848AB7C5B2769789C3C57BA079780B7516151C84897C9AFC21F'
  checksumType64= 'sha256'

  silentArgs    = "/VERYSILENT"
  validExitCodes= @(0, 3010, 1641)
}

Install-ChocolateyPackage @packageArgs










    









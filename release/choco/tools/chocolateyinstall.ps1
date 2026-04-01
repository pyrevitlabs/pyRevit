
$ErrorActionPreference = 'Stop';

$toolsDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$url64      = 'https://github.com/pyrevitlabs/pyRevit/releases/download/v6.3.0.26091%2B2238/pyRevit_CLI_6.3.0.26091_admin_signed.exe'

$packageArgs = @{
  packageName   = $env:ChocolateyPackageName
  unzipLocation = $toolsDir
  fileType      = 'exe'
  url64bit      = $url64

  softwareName  = 'pyrevit-cli*'

  checksum64    = 'C56272AA11B6757EA3254C94B558DBBA609D6339AFF3152AFC04C5A56533D014'
  checksumType64= 'sha256'

  silentArgs    = "/VERYSILENT"
  validExitCodes= @(0, 3010, 1641)
}

Install-ChocolateyPackage @packageArgs










    









$ErrorActionPreference = 'Stop'

$url64      = 'https://github.com/pyrevitlabs/pyRevit/releases/download/v7.0.0.26278%2B2233/pyRevit_7.0.0.26278_admin_signed.exe'

$packageArgs = @{
  packageName    = $env:ChocolateyPackageName
  fileType       = 'exe'
  url64bit       = $url64

  softwareName   = 'pyRevit version*'

  checksum64     = 'F7C42EB88785146334181013C56D6B80F7FCC734CF26FBA37AA283063B22045A'
  checksumType64 = 'sha256'

  silentArgs     = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
  validExitCodes = @(0, 3010, 1641)
}

Install-ChocolateyPackage @packageArgs

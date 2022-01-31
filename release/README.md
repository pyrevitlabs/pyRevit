Test commands
- Build MSI installer `msbuild .\release\pyrevit-cli.wixproj`
- Install the installer `msiexec /i "dist\pyRevit_CLI_*_signed.msi" /l*v "dist\log.txt"`
- Uninstall `msiexec.exe /x "{ProductIdCode}"` (Take code from `pyrevit-cli.props`)
- Force uninstall: Remove `pyRevit CLI` entry in `HKEY_LOCAL_MACHINE\SOFTWARE\Classes\Installer\Products\`
# Chocolatey packages

Two packages are built from this folder on every release:

| Package | Folder | Wraps |
|---|---|---|
| `pyrevit-cli` | this folder | `pyRevit_CLI_<version>_admin_signed.exe` |
| `pyrevit` | [`pyrevit/`](pyrevit) | `pyRevit_<version>_admin_signed.exe`, which includes the CLI |

The build rewrites `$url64` and `checksum64` in each `tools/chocolateyinstall.ps1` and stamps the version and copyright of each `.nuspec` (`dotnet run -c Release -- pack`), so do not edit those values by hand. The release job signs and attaches the `.nupkg` files to the draft GitHub release. After the release is published, `.github/workflows/choco.yml` pushes them to Chocolatey.

## Testing a package locally

Run `choco-test.sh [pyrevit-cli|pyrevit]` from an elevated shell. It uninstalls the package, packs it from the folder and installs it from there. The committed install scripts point at an already published release.

## Pushing again

Run the `Push Chocolatey packages` workflow with the tag of the published release. Versions the feed already has are skipped.

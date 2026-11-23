#!/bin/bash
package=${1:-pyrevit-cli}
cd "$(dirname "$0")"
if [ "$package" = "pyrevit" ]; then
  cd pyrevit
fi
choco uninstall "$package" -y
choco pack
choco install "$package" -s "'.;chocolatey'" -y

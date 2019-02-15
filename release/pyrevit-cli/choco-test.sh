#!/bin/bash
choco uninstall pyrevit-cli -y
choco pack
choco install pyrevit-cli -s "'.;chocolatey'" -y
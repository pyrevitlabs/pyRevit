<#
.SYNOPSIS
Stops the pyrevit MCP servers that run from this clone's bin folder.

.DESCRIPTION
Every MCP client session starts bin\pyrevit.exe mcp, which keeps files in bin\ open.
A rebuild fails with "The process cannot access the file ... because it is being used by
another process" until those servers are stopped. The script ends only the bare
"pyrevit.exe mcp" servers of the given bin folder, never short-lived commands such as
"pyrevit mcp install", and never a pyrevit.exe from another clone. Servers of every
client session are stopped; clients start a new one on the next tool call or need a
reconnect.

.PARAMETER BinPath
The bin folder of the clone. Defaults to bin\ of the repository this script is in.

.EXAMPLE
.\dev\scripts\Stop-McpServers.ps1 -WhatIf
Lists the servers that would be stopped.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$BinPath = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..\..')) 'bin')
)

$executable = Join-Path $BinPath 'pyrevit.exe'
$servers = @(
    Get-CimInstance Win32_Process -Filter "Name = 'pyrevit.exe'" |
        Where-Object { $_.ExecutablePath -eq $executable -and $_.CommandLine -match '\smcp"?\s*$' }
)

foreach ($server in $servers) {
    if ($PSCmdlet.ShouldProcess("pyrevit.exe mcp (PID $($server.ProcessId))", 'Stop')) {
        Stop-Process -Id $server.ProcessId -Force
    }
}

Write-Output ("Found {0} MCP server(s) running from {1}" -f $servers.Count, $BinPath)

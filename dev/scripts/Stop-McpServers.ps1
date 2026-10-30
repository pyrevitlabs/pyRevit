<#
.SYNOPSIS
Stops the pyrevit MCP servers that run from this clone's bin folder.

.DESCRIPTION
Every MCP client session starts bin\pyrevit.exe mcp, which keeps files in bin\ open.
A rebuild fails with "The process cannot access the file ... because it is being used by
another process" until those servers are stopped. The script ends only the servers of the
given bin folder: "pyrevit.exe mcp", optionally with --revit=<year>. It never ends
short-lived commands such as "pyrevit mcp install" or "pyrevit clones update mcp", nor a
pyrevit.exe from another clone. Servers of every client session are stopped; clients start
a new one on the next tool call or need a reconnect.

.PARAMETER BinPath
The bin folder of the clone, absolute or relative to the current folder. Defaults to bin\
of the repository this script is in.

.EXAMPLE
.\dev\scripts\Stop-McpServers.ps1 -WhatIf
Lists the servers that would be stopped.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$BinPath = (Join-Path $PSScriptRoot '..\..\bin')
)

$BinPath = (Resolve-Path -LiteralPath $BinPath -ErrorAction Stop).ProviderPath
$executable = Join-Path $BinPath 'pyrevit.exe'
$launcher = '^\s*(?:"?' + [regex]::Escape($executable) + '"?|"[^"]*"|\S+)'
$serverArguments = '^\s+mcp(\s+--revit=\S+)?\s*$'
$servers = @(
    Get-CimInstance Win32_Process -Filter "Name = 'pyrevit.exe'" |
        Where-Object {
            $_.ExecutablePath -eq $executable -and ($_.CommandLine -replace $launcher, '') -match $serverArguments
        }
)

$stopped = 0
foreach ($server in $servers) {
    if ($PSCmdlet.ShouldProcess("pyrevit.exe mcp (PID $($server.ProcessId))", 'Stop')) {
        try {
            Stop-Process -Id $server.ProcessId -Force -ErrorAction Stop
        }
        catch {
            if (Get-Process -Id $server.ProcessId -ErrorAction SilentlyContinue) {
                throw
            }
        }
        Wait-Process -Id $server.ProcessId -Timeout 10 -ErrorAction SilentlyContinue
        if (Get-Process -Id $server.ProcessId -ErrorAction SilentlyContinue) {
            throw "pyrevit.exe mcp (PID $($server.ProcessId)) did not exit within 10 seconds."
        }
        $stopped++
    }
}

Write-Output ("Stopped {0} of {1} MCP server(s) running from {2}" -f $stopped, $servers.Count, $BinPath)

package cli

import (
	"fmt"
	"os"
)

const version string = "0.17"
const help string = `Record pyRevit usage logs to database

Usage:
	pyrevit-telemetryserver <db_uri> [--scripts=<script_table>] [--events=<event_table>] --port=<port> [--debug] [--trace]

Options:
	-h --help                    show this screen
	-V --version                 show version
	--scripts=<script_table>     target table or collection for script logs
	--events=<event_table>       target table or collection for app event logs
	--port=<port>                server port number to listen on
	--debug                      print debug info
	--trace                      print trace info e.g. full json logs and sql queries

Supports:
	postgresql:          using github.com/lib/pq
	mongodb:             using gopkg.in/mgo.v2
	mysql:               using github.com/go-sql-driver/mysql
	sqlserver:           using github.com/denisenkom/go-mssqldb
	sqlite3:             using github.com/mattn/go-sqlite3

Examples:
	pyrevit-telemetryserver postgres://user:pass@data.mycompany.com/mydb --scripts="pyrevitlogs" --events="appevents" --port=8080 --debug
	pyrevit-telemetryserver mongodb://user:pass@localhost:27017/mydb --scripts="pyrevitlogs" --events="appevents" --port=8080
	pyrevit-telemetryserver "mysql:user:pass@tcp(localhost:3306)/tests" --scripts="pyrevitlogs" --port=8080
	pyrevit-telemetryserver sqlserver://user:pass@my-azure-db.database.windows.net?database=mydb --scripts="pyrevitlogs" --port=8080
	pyrevit-telemetryserver sqlite3:data.db --scripts="pyrevitlogs" --port=8080
`

var printHelpAndExit = func(err error, docoptMessage string) {
	if err != nil {
		// if err occured print full help
		// docopt only includes usage section in its message
		fmt.Fprintln(os.Stderr, help)
		os.Exit(1)
	} else {
		// otherwise print whatever docopt says
		// e.g. reporting version
		fmt.Println(docoptMessage)
		os.Exit(0)
	}
}

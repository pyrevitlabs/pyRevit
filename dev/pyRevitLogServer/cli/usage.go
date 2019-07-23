package cli

import (
	"fmt"
	"os"
)

const version string = "0.2"
const help string = `Record pyRevit usage logs to database

Usage:
	pyrevit-logserver <db_uri> <table> --port=<port> [--debug] [--trace]

Options:
	-h --help            show this screen
	-V --version         show version
	--port=<port>        server port number to listen on
	--debug              print debug info
	--trace              print trace info e.g. full json logs and sql queries

Supports:
	postgresql:          using github.com/lib/pq
	mongodb:             using gopkg.in/mgo.v2
	mysql:               using github.com/go-sql-driver/mysql
	sqlserver:           using github.com/denisenkom/go-mssqldb
	sqlite3:             using github.com/mattn/go-sqlite3

Examples:
	pyrevit-logserver postgres://user:pass@data.mycompany.com/mydb pyrevitlogs --port=8080 --debug
	pyrevit-logserver mongodb://user:pass@localhost:27017/mydb pyrevitlogs --port=8080
	pyrevit-logserver "mysql:user:pass@tcp(localhost:3306)/tests" pyrevitlogs --port=8080
	pyrevit-logserver sqlserver://user:pass@my-azure-db.database.windows.net?database=mydb pyrevitlogs --port=8080
	pyrevit-logserver sqlite3:data.db pyrevitlogs --port=8080
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

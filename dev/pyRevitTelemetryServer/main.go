package main

import (
	"fmt"

	"pyrevittelemetryserver/cli"
	"pyrevittelemetryserver/persistence"
	"pyrevittelemetryserver/server"
)

func main() {
	// process command line arguments
	options := cli.NewOptions()

	// log options if requested
	logger := cli.NewLogger(options)
	logger.Trace(options)
	for key, value := range *options.Opts {
		logger.Debug(fmt.Sprintf("%s=%v", key, value))
	}

	// check connection string and determine target db driver
	dbcfg, cErr := persistence.NewConfig(options)
	if cErr != nil {
		panic(cErr)
	}

	// request a db connection to read and write
	dbConn, nErr := persistence.NewConnection(dbcfg)
	if nErr != nil {
		panic(nErr)
	}

	// ask server to start and pass db writer interface
	server.Start(options, dbConn, logger)
}

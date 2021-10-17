package server

import (
	"fmt"
	"net/http"

	"pyrevittelemetryserver/cli"
	"pyrevittelemetryserver/persistence"

	"github.com/gofrs/uuid"
	"github.com/gorilla/mux"
)

var ServerId uuid.UUID

var OkMessage = "[ {g}OK{!} ]"

func Start(opts *cli.Options, dbConn persistence.Connection, logger *cli.Logger) {
	//create new id for this server instance
	ServerId = uuid.Must(uuid.NewV4())

	// http server router
	router := mux.NewRouter().StrictSlash(true)

	// create routes
	// create scripts routes
	if opts.ScriptsTable != "" {
		RouteScripts(router, opts, dbConn, logger)
	}
	// create events routes
	if opts.EventsTable != "" {
		RouteEvents(router, opts, dbConn, logger)
	}

	RouteStatus(router, opts, dbConn, logger)

	// start listening now
	logger.Print(fmt.Sprintf("Server listening on %d...", opts.Port))
	if opts.Https {
		logger.Fatal(
			http.ListenAndServeTLS(
				fmt.Sprintf(":%d", opts.Port),
				fmt.Sprintf("%s.crt", opts.ExeName),
				fmt.Sprintf("%s.key", opts.ExeName),
				router,
			))

	} else {
		logger.Fatal(
			http.ListenAndServe(
				fmt.Sprintf(":%d", opts.Port),
				router,
			))
	}
}

func GetStatus() string {
	return "pass" // "pass", "fail" or "warn"
}

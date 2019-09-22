package server

import (
	"fmt"
	"net/http"

	"../cli"
	"../persistence"
	"github.com/gorilla/mux"
)

var OkMessage = "[ {g}OK{!} ]"

func Start(opts *cli.Options, dbConn persistence.Connection, logger *cli.Logger) {
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
	logger.Fatal(
		http.ListenAndServe(
			fmt.Sprintf(":%d", opts.Port),
			router,
		))
}

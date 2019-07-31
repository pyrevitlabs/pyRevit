package server

import (
	"encoding/json"
	"fmt"
	"net/http"

	"../cli"
	"../persistence"
	"github.com/gorilla/mux"
)

func Start(opts *cli.Options, dbConn persistence.Connection, logger *cli.Logger) {
	// http server router
	router := mux.NewRouter().StrictSlash(true)

	// create routes

	// POST /
	// create new telemetry record
	// https://stackoverflow.com/a/26212073
	router.HandleFunc("/api/v1", func(w http.ResponseWriter, r *http.Request) {
		// parse given json data into a new record
		logrec := persistence.TelemetryRecord{}
		decodeErr := json.NewDecoder(r.Body).Decode(&logrec)
		if decodeErr != nil {
			logger.Debug(decodeErr)
			return
		}

		// now write to db
		_, dbWriteErr := dbConn.Write(&logrec, logger)
		if dbWriteErr != nil {
			logger.Debug(dbWriteErr)
			logrec.PrintRecordInfo(logger, fmt.Sprintf("[ {r}%s{!} ]", dbWriteErr))
		} else {
			logrec.PrintRecordInfo(logger, "[ {g}OK{!} ]")
		}

		// dump the telemetry record json data if requested
		jsonData, responseDataErr := json.Marshal(logrec)
		if responseDataErr == nil {
			jsonString := string(jsonData)
			if logger.PrintTrace {
				logger.Trace(jsonString)
			}

			// write response
			_, responseErr := w.Write([]byte(jsonString))
			if responseErr != nil {
				logger.Debug(responseErr)
			}
		} else {
			logger.Debug(responseDataErr)
		}

	}).Methods("POST")

	// GET /
	// get recorded telemetry record
	router.HandleFunc("/api/v1", func(w http.ResponseWriter, r *http.Request) {

	}).Methods("GET")

	// start listening now
	logger.Print(fmt.Sprintf("Server listening on %d...", opts.Port))
	logger.Fatal(
		http.ListenAndServe(
			fmt.Sprintf(":%d", opts.Port),
			router,
		))
}

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

	// POST script/
	// create new script telemetry record
	// https://stackoverflow.com/a/26212073
	router.HandleFunc("/api/v1/scripts/", func(w http.ResponseWriter, r *http.Request) {
		// parse given json data into a new record
		logrec := persistence.ScriptTelemetryRecord{}
		decodeErr := json.NewDecoder(r.Body).Decode(&logrec)
		if decodeErr != nil {
			logger.Debug(decodeErr)
			return
		}

		// now write to db
		_, dbWriteErr := dbConn.WriteScriptTelemetry(&logrec, logger)
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

	// GET script/
	// get recorded telemetry record
	router.HandleFunc("/api/v1/scripts/", func(w http.ResponseWriter, r *http.Request) {

	}).Methods("GET")

	// POST script/
	// create new script telemetry record
	// https://stackoverflow.com/a/26212073
	router.HandleFunc("/api/v1/events/", func(w http.ResponseWriter, r *http.Request) {
		// parse given json data into a new record
		logrec := persistence.EventTelemetryRecord{}
		decodeErr := json.NewDecoder(r.Body).Decode(&logrec)
		if decodeErr != nil {
			logger.Debug(decodeErr)
			return
		}

		// now write to db
		_, dbWriteErr := dbConn.WriteEventTelemetry(&logrec, logger)
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

	// GET script/
	// get recorded telemetry record
	router.HandleFunc("/api/v1/events/", func(w http.ResponseWriter, r *http.Request) {

	}).Methods("GET")

	// start listening now
	logger.Print(fmt.Sprintf("Server listening on %d...", opts.Port))
	logger.Fatal(
		http.ListenAndServe(
			fmt.Sprintf(":%d", opts.Port),
			router,
		))
}

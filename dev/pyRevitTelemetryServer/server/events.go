package server

import (
	"encoding/json"
	"fmt"
	"net/http"

	"pyrevittelemetryserver/cli"
	"pyrevittelemetryserver/persistence"

	"github.com/gorilla/mux"
)

func dumpEventAndRespond(logrec interface{}, w http.ResponseWriter, logger *cli.Logger) {
	// dump the telemetry record json data if requested
	jsonData, responseDataErr := json.Marshal(logrec)
	if responseDataErr == nil {
		jsonString := string(jsonData)
		if logger.PrintTrace {
			logger.Trace(jsonString)
		}

		// write response
		w.Header().Set("Content-Type", "application/json")
		_, responseErr := w.Write([]byte(jsonString))
		if responseErr != nil {
			logger.Debug(responseErr)
		}
	} else {
		logger.Debug(responseDataErr)
	}
}

func RouteEvents(router *mux.Router, opts *cli.Options, dbConn persistence.Connection, logger *cli.Logger) {
	// POST events/
	// create new script telemetry record
	// https://stackoverflow.com/a/26212073
	router.HandleFunc("/api/v2/events/", func(w http.ResponseWriter, r *http.Request) {
		// parse given json data into a new record
		logrec := persistence.EventTelemetryRecordV2{}
		decodeErr := json.NewDecoder(r.Body).Decode(&logrec)
		if decodeErr != nil {
			logger.Debug(decodeErr)
			return
		}

		err := logrec.Validate()
		if err != nil {
			// log error
			logrec.PrintRecordInfo(logger, fmt.Sprintf("[ {r}%s{!} ]", err.Error()))
			// respond with error
			w.WriteHeader(http.StatusBadRequest)
			respondError(err, w, logger)
		} else {
			// now write to db
			_, dbWriteErr := dbConn.WriteEventTelemetryV2(&logrec, logger)
			if dbWriteErr != nil {
				logger.Debug(dbWriteErr)
				logrec.PrintRecordInfo(logger, fmt.Sprintf("[ {r}%s{!} ]", dbWriteErr))
			} else {
				logrec.PrintRecordInfo(logger, OkMessage)
			}
			// respond with the created data
			dumpEventAndRespond(logrec, w, logger)
		}

	}).Methods("POST")

	// GET events/
	// get recorded telemetry record
	router.HandleFunc("/api/v2/events/", func(w http.ResponseWriter, r *http.Request) {

	}).Methods("GET")
}

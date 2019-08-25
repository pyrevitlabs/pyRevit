package server

import (
	"encoding/json"
	"fmt"
	"net/http"

	"../cli"
	"../persistence"
	"github.com/gorilla/mux"
)

func dumpAndRespond(logrec interface{}, w http.ResponseWriter, logger *cli.Logger) {
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
}

func RouteScripts(router *mux.Router, opts *cli.Options, dbConn persistence.Connection, logger *cli.Logger) {
	// POST scripts/
	// create new script telemetry record
	// https://stackoverflow.com/a/26212073
	router.HandleFunc("/api/v1/scripts/", func(w http.ResponseWriter, r *http.Request) {
		// parse given json data into a new record
		logrec := persistence.ScriptTelemetryRecordV1{}
		decodeErr := json.NewDecoder(r.Body).Decode(&logrec)
		if decodeErr != nil {
			logger.Debug(decodeErr)
			return
		}

		// now write to db
		_, dbWriteErr := dbConn.WriteScriptTelemetryV1(&logrec, logger)
		if dbWriteErr != nil {
			logger.Debug(dbWriteErr)
			logrec.PrintRecordInfo(logger, fmt.Sprintf("[ {r}%s{!} ]", dbWriteErr))
		} else {
			logrec.PrintRecordInfo(logger, OkMessage)
		}

		dumpAndRespond(logrec, w, logger)

	}).Methods("POST")

	router.HandleFunc("/api/v2/scripts/", func(w http.ResponseWriter, r *http.Request) {
		// parse given json data into a new record
		logrec := persistence.ScriptTelemetryRecordV2{}
		decodeErr := json.NewDecoder(r.Body).Decode(&logrec)
		if decodeErr != nil {
			logger.Debug(decodeErr)
			return
		}

		// now write to db
		_, dbWriteErr := dbConn.WriteScriptTelemetryV2(&logrec, logger)
		if dbWriteErr != nil {
			logger.Debug(dbWriteErr)
			logrec.PrintRecordInfo(logger, fmt.Sprintf("[ {r}%s{!} ]", dbWriteErr))
		} else {
			logrec.PrintRecordInfo(logger, OkMessage)
		}

		dumpAndRespond(logrec, w, logger)

	}).Methods("POST")

	// GET scripts/
	// get recorded telemetry record
	router.HandleFunc("/api/v1/scripts/", func(w http.ResponseWriter, r *http.Request) {

	}).Methods("GET")

	router.HandleFunc("/api/v2/scripts/", func(w http.ResponseWriter, r *http.Request) {

	}).Methods("GET")
}

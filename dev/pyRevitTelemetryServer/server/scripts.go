package server

import (
	"encoding/json"
	"fmt"
	"net/http"

	"pyrevittelemetryserver/cli"
	"pyrevittelemetryserver/persistence"

	"github.com/gorilla/mux"
)

func respondError(err error, w http.ResponseWriter, logger *cli.Logger) {
	// write response
	message := err.Error()
	logger.Debug("vaidation error: ", message)
	_, responseErr := w.Write([]byte(message))
	if responseErr != nil {
		logger.Debug(responseErr)
	}
}

func dumpScriptAndRespond(logrec interface{}, w http.ResponseWriter, logger *cli.Logger) {
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

		err := logrec.Validate()
		if err != nil {
			// log error
			logrec.PrintRecordInfo(logger, fmt.Sprintf("[ {r}%s{!} ]", err.Error()))
			// respond with error
			w.WriteHeader(http.StatusBadRequest)
			respondError(err, w, logger)
		} else {
			// now write to db
			_, dbWriteErr := dbConn.WriteScriptTelemetryV1(&logrec, logger)
			if dbWriteErr != nil {
				logger.Debug(dbWriteErr)
				logrec.PrintRecordInfo(logger, fmt.Sprintf("[ {r}%s{!} ]", dbWriteErr))
			} else {
				logrec.PrintRecordInfo(logger, OkMessage)
			}
			// respond with the created data
			dumpScriptAndRespond(logrec, w, logger)
		}

	}).Methods("POST")

	router.HandleFunc("/api/v2/scripts/", func(w http.ResponseWriter, r *http.Request) {
		// parse given json data into a new record
		logrec := persistence.ScriptTelemetryRecordV2{}
		decodeErr := json.NewDecoder(r.Body).Decode(&logrec)
		if decodeErr != nil {
			logger.Debug(decodeErr)
			return
		}

		// validate
		err := logrec.Validate()
		if err != nil {
			// log error
			logrec.PrintRecordInfo(logger, fmt.Sprintf("[ {r}%s{!} ]", err.Error()))
			// respond with error
			w.WriteHeader(http.StatusBadRequest)
			respondError(err, w, logger)
		} else {
			// now write to db
			_, dbWriteErr := dbConn.WriteScriptTelemetryV2(&logrec, logger)
			if dbWriteErr != nil {
				logger.Debug(dbWriteErr)
				logrec.PrintRecordInfo(logger, fmt.Sprintf("[ {r}%s{!} ]", dbWriteErr))
			} else {
				logrec.PrintRecordInfo(logger, OkMessage)
			}
			// respond with the created data
			dumpScriptAndRespond(logrec, w, logger)
		}

	}).Methods("POST")

	// GET scripts/
	// get recorded telemetry record
	router.HandleFunc("/api/v1/scripts/", func(w http.ResponseWriter, r *http.Request) {

	}).Methods("GET")

	router.HandleFunc("/api/v2/scripts/", func(w http.ResponseWriter, r *http.Request) {

	}).Methods("GET")
}

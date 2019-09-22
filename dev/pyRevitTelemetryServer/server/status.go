package server

import (
	"encoding/json"
	"net/http"

	"../cli"
	"../persistence"
	"github.com/gorilla/mux"
)

type StatusReport struct {
	Status             string                 `json:"status"`
	CliOptions         cli.Options            `json:"cli_options"`
	DBConnetionConfigs persistence.Connection `json:"db_configs"`
}

func getServerStatus() string {
	return "healthy"
}

func prepareAndReportStatus(w http.ResponseWriter, opts *cli.Options, dbConn persistence.Connection, logger *cli.Logger) {
	// create status report data
	jsonData, responseDataErr := json.Marshal(
		StatusReport{
			Status:             getServerStatus(),
			CliOptions:         *opts,
			DBConnetionConfigs: dbConn,
		})
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

func RouteStatus(router *mux.Router, opts *cli.Options, dbConn persistence.Connection, logger *cli.Logger) {
	// GET scripts/
	// get recorded telemetry record
	router.HandleFunc("/api/v1/status", func(w http.ResponseWriter, r *http.Request) {
		prepareAndReportStatus(w, opts, dbConn, logger)
	}).Methods("GET")

	router.HandleFunc("/api/v2/status", func(w http.ResponseWriter, r *http.Request) {
		prepareAndReportStatus(w, opts, dbConn, logger)
	}).Methods("GET")
}

// https://inadarei.github.io/rfc-healthcheck/
package server

import (
	"encoding/json"
	"net/http"

	"pyrevittelemetryserver/cli"
	"pyrevittelemetryserver/persistence"

	"github.com/gorilla/mux"
)

type ServerStatus struct {
	Status    string                                  `json:"status"`
	Version   string                                  `json:"version"`
	Output    string                                  `json:"output"`
	ServiceId string                                  `json:"serviceid"`
	Checks    map[string]persistence.ConnectionStatus `json:"checks"`
}

func prepareAndReportStatus(w http.ResponseWriter, opts *cli.Options, dbConn persistence.Connection, logger *cli.Logger) {
	// create status report data
	jsonData, responseDataErr := json.Marshal(
		ServerStatus{
			Status:    GetStatus(),
			Version:   opts.Version,
			ServiceId: ServerId.String(),
			Checks: map[string]persistence.ConnectionStatus{
				string(dbConn.GetType()): dbConn.GetStatus(logger),
			},
		})
	if responseDataErr == nil {
		jsonString := string(jsonData)
		if logger.PrintTrace {
			logger.Trace(jsonString)
		}

		// write response
		w.Header().Set("Content-Type", "application/health+json")
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

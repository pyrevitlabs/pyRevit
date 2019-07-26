package server

import (
	"encoding/json"
	"fmt"
	"net/http"

	"../cli"
	"../persistence"
	"github.com/gorilla/mux"
)

func Start(opts *cli.Options, writer persistence.Writer, logger *cli.Logger) {
	router := mux.NewRouter().StrictSlash(true)
	// https://stackoverflow.com/a/26212073
	router.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		logrec := persistence.LogRecord{}
		derr := json.NewDecoder(r.Body).Decode(&logrec)
		if derr != nil {
			logger.Debug(derr)
			return
		}

		if logger.PrintTrace {
			logjson, merr := json.Marshal(logrec)
			if merr == nil {
				logger.Trace(string(logjson))
			}
		}

		// now write to db
		message := "[ {g}OK{!} ]"
		_, werr := writer.Write(&logrec, logger)
		if werr != nil {
			logger.Debug(werr)
			message = fmt.Sprintf("[ {r}%s{!} ]", werr)
		}

		if logrec.LogMeta.SchemaVersion == "" {
			logger.Print(fmt.Sprintf(
				"%s %s-%s %q %s:%s [%s.%s] code=%d info=%v",
				message,
				logrec.Date,
				logrec.Time,
				logrec.UserName,
				logrec.RevitBuild,
				logrec.TraceInfo.EngineInfo.Version,
				logrec.ExtensionName,
				logrec.CommandName,
				logrec.ResultCode,
				logrec.CommandResults,
			))
		} else if logrec.LogMeta.SchemaVersion == "2.0" {
			logger.Print(fmt.Sprintf(
				"%s %s %q %s:%s (%s) [%s.%s] code=%d info=%v",
				message,
				logrec.TimeStamp,
				logrec.UserName,
				logrec.RevitBuild,
				logrec.TraceInfo.EngineInfo.Version,
				logrec.TraceInfo.EngineInfo.Type,
				logrec.ExtensionName,
				logrec.CommandName,
				logrec.ResultCode,
				logrec.CommandResults,
			))
		}

		// logger.Debug(res.Message)

	}).Methods("POST")

	logger.Print(fmt.Sprintf("Server listening on %d...", opts.Port))
	logger.Fatal(http.ListenAndServe(fmt.Sprintf(":%d", opts.Port), router))
}

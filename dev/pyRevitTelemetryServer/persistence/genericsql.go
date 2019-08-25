package persistence

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"../cli"

	_ "github.com/denisenkom/go-mssqldb"
	_ "github.com/go-sql-driver/mysql"
	_ "github.com/lib/pq"
	_ "github.com/mattn/go-sqlite3"

	uuid "github.com/satori/go.uuid"
)

type GenericSQLConnection struct {
	DatabaseConnection
}

func (w GenericSQLConnection) WriteScriptTelemetryV1(logrec *ScriptTelemetryRecordV1, logger *cli.Logger) (*Result, error) {
	// generate generic sql insert query
	logger.Debug("generating query")
	query, qErr := generateScriptInsertQueryV1(w.Config.ScriptTarget, logrec, logger)
	if qErr != nil {
		return nil, qErr
	}

	return commitSQL(w.Config.Backend, w.Config.ConnString, query, logger)
}

func (w GenericSQLConnection) WriteScriptTelemetryV2(logrec *ScriptTelemetryRecordV2, logger *cli.Logger) (*Result, error) {
	// generate generic sql insert query
	logger.Debug("generating query")
	query, qErr := generateScriptInsertQueryV2(w.Config.ScriptTarget, logrec, logger)
	if qErr != nil {
		return nil, qErr
	}

	return commitSQL(w.Config.Backend, w.Config.ConnString, query, logger)
}

func (w GenericSQLConnection) WriteEventTelemetryV2(logrec *EventTelemetryRecordV2, logger *cli.Logger) (*Result, error) {
	// generate generic sql insert query
	logger.Debug("generating query")
	query, qErr := generateEventInsertQueryV2(w.Config.EventTarget, logrec, logger)
	if qErr != nil {
		return nil, qErr
	}

	return commitSQL(w.Config.Backend, w.Config.ConnString, query, logger)
}

func commitSQL(backend DBBackendName, connStr string, query string, logger *cli.Logger) (*Result, error) {
	// open connection
	db, err := openConnection(backend, connStr, logger)
	if err != nil {
		logger.Debug("error opening connection")
		return nil, err
	}
	defer db.Close()

	// start transaction
	logger.Debug("opening transaction")
	tx, beginErr := db.Begin()
	if beginErr != nil {
		logger.Debug("error opening transaction")
		return nil, beginErr
	}
	defer tx.Rollback()

	// run the insert query
	logger.Debug("executing insert query")
	_, eErr := db.Exec(query)
	if eErr != nil {
		return nil, eErr
	}

	// commit transaction
	logger.Debug("commiting transaction")
	txnErr := tx.Commit()
	if txnErr != nil {
		return nil, txnErr
	}

	logger.Debug("preparing report")
	return &Result{
		Message: "successfully inserted usage record",
	}, nil
}

func openConnection(backend DBBackendName, connStr string, logger *cli.Logger) (*sql.DB, error) {
	// open connection
	logger.Debug(fmt.Sprintf("opening %s connection", backend))
	cleanConnStr := connStr
	if backend == Sqlite || backend == MySql {
		cleanConnStr = strings.Replace(connStr, string(backend)+":", "", 1)
	}
	return sql.Open(string(backend), cleanConnStr)
}

func generateScriptInsertQueryV1(table string, logrec *ScriptTelemetryRecordV1, logger *cli.Logger) (string, error) {
	// read csv file and build sql insert query
	var querystr strings.Builder

	logger.Debug("generating insert query with-out headers")
	querystr.WriteString(fmt.Sprintf("INSERT INTO %s values ", table))

	// build sql data info
	logger.Debug("building insert query for data")
	datalines := make([]string, 0)

	cresults, merr := json.Marshal(logrec.CommandResults)
	if merr != nil {
		logger.Debug("error logging command results")
	}

	// create record based on schema
	var record []string

	// generate record id, panic if error
	recordId := uuid.Must(uuid.NewV4())

	re := regexp.MustCompile(`(\d+:\d+:\d+)`)
	record = []string{
		recordId.String(),
		logrec.Date,
		re.FindString(logrec.Time),
		logrec.UserName,
		logrec.RevitVersion,
		logrec.RevitBuild,
		logrec.SessionId,
		logrec.PyRevitVersion,
		strconv.FormatBool(logrec.IsDebugMode),
		strconv.FormatBool(logrec.IsConfigMode),
		logrec.CommandName,
		logrec.BundleName,
		logrec.ExtensionName,
		logrec.CommandUniqueName,
		strconv.Itoa(logrec.ResultCode),
		string(cresults),
		logrec.ScriptPath,
		logrec.TraceInfo.EngineInfo.Version,
		logrec.TraceInfo.IronPythonTraceDump,
		logrec.TraceInfo.CLRTraceDump,
	}

	datalines = append(datalines, ToSql(&record, true))

	// add csv records to query string
	all_datalines := strings.Join(datalines, ", ")
	logger.Trace(all_datalines)
	querystr.WriteString(all_datalines)
	querystr.WriteString(";\n")
	logger.Debug("building query completed")

	// execute query
	full_query := querystr.String()
	logger.Trace(full_query)
	return full_query, nil
}

func generateScriptInsertQueryV2(table string, logrec *ScriptTelemetryRecordV2, logger *cli.Logger) (string, error) {
	// read csv file and build sql insert query
	var querystr strings.Builder

	logger.Debug("generating insert query with-out headers")
	querystr.WriteString(fmt.Sprintf("INSERT INTO %s values ", table))

	// build sql data info
	logger.Debug("building insert query for data")
	datalines := make([]string, 0)

	// marshal json data
	engineCfgs, merr := json.Marshal(logrec.EngineCfgs)
	if merr != nil {
		logger.Debug("error logging engine configs")
	}

	// marshal json data
	cresults, merr := json.Marshal(logrec.CommandResults)
	if merr != nil {
		logger.Debug("error logging command results")
	}

	// create record based on schema
	var record []string

	// generate record id, panic if error
	recordId := uuid.Must(uuid.NewV4())

	record = []string{
		recordId.String(),
		logrec.TimeStamp,
		logrec.UserName,
		logrec.RevitVersion,
		logrec.RevitBuild,
		logrec.SessionId,
		logrec.PyRevitVersion,
		logrec.Clone,
		strconv.FormatBool(logrec.IsDebugMode),
		strconv.FormatBool(logrec.IsConfigMode),
		strconv.FormatBool(logrec.IsExecFromGUI),
		string(engineCfgs),
		logrec.CommandName,
		logrec.BundleName,
		logrec.ExtensionName,
		logrec.CommandUniqueName,
		logrec.DocumentName,
		logrec.DocumentPath,
		strconv.Itoa(logrec.ResultCode),
		string(cresults),
		logrec.ScriptPath,
		logrec.TraceInfo.EngineInfo.Type,
		logrec.TraceInfo.EngineInfo.Version,
		logrec.TraceInfo.Message,
	}
	datalines = append(datalines, ToSql(&record, true))

	// add csv records to query string
	all_datalines := strings.Join(datalines, ", ")
	logger.Trace(all_datalines)
	querystr.WriteString(all_datalines)
	querystr.WriteString(";\n")
	logger.Debug("building query completed")

	// execute query
	full_query := querystr.String()
	logger.Trace(full_query)
	return full_query, nil
}

func generateEventInsertQueryV2(table string, logrec *EventTelemetryRecordV2, logger *cli.Logger) (string, error) {
	// read csv file and build sql insert query
	var querystr strings.Builder

	logger.Debug("generating insert query with-out headers")
	querystr.WriteString(fmt.Sprintf("INSERT INTO %s values ", table))

	// build sql data info
	logger.Debug("building insert query for data")
	datalines := make([]string, 0)

	// marshal json data
	cresults, merr := json.Marshal(logrec.EventArgs)
	if merr != nil {
		logger.Debug("error logging command results")
	}

	// create record based on schema
	var record []string

	// generate record id, panic if error
	recordId := uuid.Must(uuid.NewV4())

	record = []string{
		recordId.String(),
		logrec.TimeStamp,
		logrec.EventType,
		string(cresults),
		logrec.UserName,
		logrec.HostUserName,
		logrec.RevitVersion,
		logrec.RevitBuild,
		strconv.FormatBool(logrec.Cancellable),
		strconv.FormatBool(logrec.Cancelled),
		strconv.Itoa(logrec.DocumentId),
		logrec.DocumentType,
		logrec.DocumentTemplate,
		logrec.DocumentName,
		logrec.DocumentPath,
		logrec.ProjectNumber,
		logrec.ProjectName,
	}
	datalines = append(datalines, ToSql(&record, true))

	// add csv records to query string
	all_datalines := strings.Join(datalines, ", ")
	logger.Trace(all_datalines)
	querystr.WriteString(all_datalines)
	querystr.WriteString(";\n")
	logger.Debug("building query completed")

	// execute query
	full_query := querystr.String()
	logger.Trace(full_query)
	return full_query, nil
}

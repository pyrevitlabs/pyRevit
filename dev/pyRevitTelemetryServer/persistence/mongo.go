package persistence

import (
	"pyrevittelemetryserver/cli"

	_ "github.com/lib/pq"
	"gopkg.in/mgo.v2"
)

type MongoDBConnection struct {
	DatabaseConnection
}

func (w MongoDBConnection) GetType() DBBackend {
	return w.Config.Backend
}

func (w MongoDBConnection) GetVersion(logger *cli.Logger) string {
	// parse and grab database name from uri
	logger.Debug("grabbing db name from connection string")
	dialinfo, err := mgo.ParseURL(w.Config.ConnString)
	if err != nil {
		return ""
	}

	logger.Debug("opening mongodb session")
	session, cErr := mgo.DialWithInfo(dialinfo)
	if cErr != nil {
		return ""
	}
	defer session.Close()

	logger.Debug("getting mongodb version")
	buildInfo, vErr := session.BuildInfo()
	if vErr != nil {
		return ""
	}

	return buildInfo.Version
}

func (w MongoDBConnection) GetStatus(logger *cli.Logger) ConnectionStatus {
	return ConnectionStatus{
		Status:  "pass",
		Version: w.GetVersion(logger),
	}
}

func (w MongoDBConnection) WriteScriptTelemetryV1(logrec *ScriptTelemetryRecordV1, logger *cli.Logger) (*Result, error) {
	return commitMongo(w.Config.ConnString, w.Config.ScriptTarget, logrec, logger)
}

func (w MongoDBConnection) WriteScriptTelemetryV2(logrec *ScriptTelemetryRecordV2, logger *cli.Logger) (*Result, error) {
	return commitMongo(w.Config.ConnString, w.Config.ScriptTarget, logrec, logger)
}

func (w MongoDBConnection) WriteEventTelemetryV2(logrec *EventTelemetryRecordV2, logger *cli.Logger) (*Result, error) {
	return commitMongo(w.Config.ConnString, w.Config.EventTarget, logrec, logger)
}

func commitMongo(connStr string, targetCollection string, logrec interface{}, logger *cli.Logger) (*Result, error) {
	// parse and grab database name from uri
	logger.Debug("grabbing db name from connection string")
	dialinfo, err := mgo.ParseURL(connStr)
	if err != nil {
		return nil, err
	}

	logger.Debug("opening mongodb session")
	session, cErr := mgo.DialWithInfo(dialinfo)
	if cErr != nil {
		return nil, cErr
	}
	defer session.Close()

	// Optional. Switch the session to a monotonic behavior.
	logger.Debug("setting session properties")
	session.SetMode(mgo.Monotonic, true)
	logger.Trace(session)

	logger.Debug("getting target collection")
	db := session.DB(dialinfo.Database)
	c := db.C(targetCollection)
	logger.Trace(c)

	logger.Debug("opening bulk operation")
	bulkop := c.Bulk()

	// build sql data info
	logger.Debug("building documents")
	bulkop.Insert(logrec)

	logger.Debug("running bulk operation")
	_, txnErr := bulkop.Run()
	if txnErr != nil {
		return nil, txnErr
	}

	// compact collection if requested
	logger.Debug("preparing report")
	return &Result{
		Message: "successfully inserted usage document",
	}, nil
}

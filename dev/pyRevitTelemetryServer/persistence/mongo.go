package persistence

import (
	"../cli"
	_ "github.com/lib/pq"
	"gopkg.in/mgo.v2"
)

type MongoDBConnection struct {
	DatabaseConnection
}

func (w MongoDBConnection) WriteScriptTelemetry(logrec *ScriptTelemetryRecord, logger *cli.Logger) (*Result, error) {
	return commitMongo(w.Config.ConnString, w.Config.ScriptTarget, logrec, logger)
}

func (w MongoDBConnection) WriteEventTelemetry(logrec *EventTelemetryRecord, logger *cli.Logger) (*Result, error) {
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

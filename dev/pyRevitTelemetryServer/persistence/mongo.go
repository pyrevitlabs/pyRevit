package persistence

import (
	"context"
	"fmt"
	"net/url"
	"pyrevittelemetryserver/cli"
	"strings"
	"time"

	_ "github.com/lib/pq"
	"go.mongodb.org/mongo-driver/v2/bson"
	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"
	"go.mongodb.org/mongo-driver/v2/mongo/readpref"
)

type MongoDBConnection struct {
	DatabaseConnection
}

func (w MongoDBConnection) GetType() DBBackend {
	return w.Config.Backend
}

func (w MongoDBConnection) GetVersion(logger *cli.Logger) string {
	logger.Debug("grabbing db name from connection string")
	logger.Debug("opening mongodb session")
	client, err := mongo.Connect(options.Client().ApplyURI(w.Config.ConnString))
	if err != nil {
		return ""
	}
	defer func() {
		disconnectCtx, disconnectCancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer disconnectCancel()
		if dErr := client.Disconnect(disconnectCtx); dErr != nil {
			panic(dErr)
		}
	}()

	pingCtx, pingCancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer pingCancel()
	pErr := client.Ping(pingCtx, readpref.Primary())

	if pErr != nil {
		return ""
	}

	// get version from admin DB
	// is this the best way of doing this?
	logger.Debug("getting mongodb version")
	var commandResult bson.M
	command := bson.D{{"buildInfo", 1}}
	cmdCtx, cmdCancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cmdCancel()
	vErr := client.Database("admin").RunCommand(cmdCtx, command).Decode(&commandResult)

	if vErr != nil {
		return ""
	}

	// parse version field to get version information
	ver := fmt.Sprintf("%+v", commandResult["version"])
	return ver
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

// mongoDatabaseFromURI extracts the database name from a MongoDB connection URI (e.g. mongodb://host/dbname -> dbname).
func mongoDatabaseFromURI(connStr string) (string, error) {
	u, err := url.Parse(connStr)
	if err != nil {
		return "", err
	}
	dbName := strings.TrimPrefix(u.Path, "/")
	if i := strings.Index(dbName, "?"); i >= 0 {
		dbName = dbName[:i]
	}
	if dbName == "" {
		dbName = "admin"
	}
	return dbName, nil
}

func commitMongo(connStr string, targetCollection string, logrec interface{}, logger *cli.Logger) (*Result, error) {
	logger.Debug("check connection string")
	dbName, err := mongoDatabaseFromURI(connStr)
	if err != nil {
		return nil, err
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	logger.Debug("opening mongodb session using connection string")
	client, err := mongo.Connect(options.Client().ApplyURI(connStr))
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = client.Disconnect(ctx)
	}()

	logger.Trace(client)

	logger.Debug("getting target collection")
	db := client.Database(dbName)
	// c := db.C(targetCollection)
	c := db.Collection(targetCollection)
	logger.Trace(c)

	logger.Debug("opening bulk operation")
	// bulkop := c.Bulk()

	// build sql data info
	logger.Debug("building documents")

	iCtx, iCancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer iCancel()

	logger.Debug("inserting new document")
	_, txnErr := c.InsertOne(iCtx, logrec)

	if txnErr != nil {
		return nil, txnErr
	}

	// compact collection if requested
	logger.Debug("preparing report")
	return &Result{
		Message: "successfully inserted usage document",
	}, nil
}

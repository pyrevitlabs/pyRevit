package persistence

import (
	"context"
	"fmt"
	"pyrevittelemetryserver/cli"
	"time"

	_ "github.com/lib/pq"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"go.mongodb.org/mongo-driver/mongo/readpref"
	"go.mongodb.org/mongo-driver/x/mongo/driver/connstring"
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
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	logger.Debug("opening mongodb session")
	client, err := mongo.Connect(ctx, options.Client().ApplyURI(w.Config.ConnString))

	defer func() {
		if err = client.Disconnect(ctx); err != nil {
			panic(err)
		}
	}()

	ctx, cancel = context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	pErr := client.Ping(ctx, readpref.Primary())

	if pErr != nil {
		return ""
	}

	// get version from admin DB
	// is this the best way of doing this?
	logger.Debug("getting mongodb version")
	var commandResult bson.M
	command := bson.D{{"buildInfo", 1}}
	vErr := client.Database("admin").RunCommand(ctx, command).Decode(&commandResult)

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

func commitMongo(connStr string, targetCollection string, logrec interface{}, logger *cli.Logger) (*Result, error) {
	// parse and grab database name from uri
	logger.Debug("check connection string")
	connStringInfo, err := connstring.ParseAndValidate(connStr)

	if err != nil {
		return nil, err
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	logger.Debug("opening mongodb session using connection string")
	client, err := mongo.Connect(ctx, options.Client().ApplyURI(connStr))

	if err != nil {
		return nil, err
	}

	logger.Trace(client)

	logger.Debug("getting target collection")
	// db := session.DB(dialinfo.Database)
	db := client.Database(connStringInfo.Database)
	// c := db.C(targetCollection)
	c := db.Collection(targetCollection)
	logger.Trace(c)

	logger.Debug("opening bulk operation")
	// bulkop := c.Bulk()

	// build sql data info
	logger.Debug("building documents")

	iCtx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

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

package persistence

import (
	"strings"

	"pyrevittelemetryserver/cli"

	"github.com/pkg/errors"
)

type DBBackend string

const (
	Postgres DBBackend = "postgres"
	MongoDB  DBBackend = "mongodb"
	MySql    DBBackend = "mysql"
	MSSql    DBBackend = "sqlserver"
	Sqlite   DBBackend = "sqlite3"
)

type Config struct {
	Backend      DBBackend `json:"backend"`
	ConnString   string    `json:"connection_string"`
	ScriptTarget string    `json:"script_target"`
	EventTarget  string    `json:"event_target"`
}

func NewConfig(options *cli.Options) (*Config, error) {
	backend, err := parseUri(options.ConnString)
	if err != nil {
		return nil, err
	}

	return &Config{
		Backend:      backend,
		ConnString:   options.ConnString,
		ScriptTarget: options.ScriptsTable,
		EventTarget:  options.EventsTable,
	}, nil
}

func parseUri(connString string) (DBBackend, error) {
	if strings.HasPrefix(connString, "postgres:") {
		return Postgres, nil
	} else if strings.HasPrefix(connString, "mongodb:") {
		return MongoDB, nil
	} else if strings.HasPrefix(connString, "mysql:") {
		return MySql, nil
	} else if strings.HasPrefix(connString, "sqlserver:") {
		return MSSql, nil
	} else if strings.HasPrefix(connString, "sqlite3:") {
		return Sqlite, nil
	} else {
		return "", errors.New("db is not yet supported")
	}
}

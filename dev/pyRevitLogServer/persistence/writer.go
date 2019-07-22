package persistence

import (
	"../cli"
)

// ErroCodes
// 0: All OK
// 1: No data to write
// 2: data is available but did not get pushed under dry run
// 3: headers are required
type Result struct {
	ResultCode int
	Message    string
}

type DatabaseWriter struct {
	Config *Config
}

type Writer interface {
	Write(*LogRecord, *cli.Logger) (*Result, error)
}

func NewWriter(dbcfg *Config) (Writer, error) {
	w := DatabaseWriter{
		Config: dbcfg,
	}
	if dbcfg.Backend == Postgres {
		return GenericSQLWriter{w}, nil
	}
	// else if dbConfig.Backend == MongoDB {
	// 	return MongoDBWriter{*w}, nil
	// } else if dbConfig.Backend == MySql {
	// 	return GenericSQLWriter{*w}, nil
	// } else if dbConfig.Backend == MSSql {
	// 	return GenericSQLWriter{*w}, nil
	// } else if dbConfig.Backend == Sqlite {
	// 	return GenericSQLWriter{*w}, nil
	// }
	// ... other writers

	panic("should not get here")
}

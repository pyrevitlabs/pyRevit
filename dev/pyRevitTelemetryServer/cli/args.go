package cli

import (
	"os"

	"github.com/docopt/docopt-go"
)

type Options struct {
	Opts         *docopt.Opts
	ConnString   string
	ScriptsTable string
	EventsTable  string
	Port         int
	Debug        bool
	Trace        bool
}

func NewOptions() *Options {
	argv := os.Args[1:]

	parser := &docopt.Parser{
		HelpHandler: printHelpAndExit,
	}

	opts, _ := parser.ParseArgs(help, argv, version)

	connString, _ := opts.String("<db_uri>")
	scriptTable, _ := opts.String("--scripts")
	eventTable, _ := opts.String("--events")
	port, _ := opts.Int("--port")

	debug, _ := opts.Bool("--debug")
	trace, _ := opts.Bool("--trace")

	return &Options{
		Opts:         &opts,
		ConnString:   connString,
		ScriptsTable: scriptTable,
		EventsTable:  eventTable,
		Port:         port,
		Debug:        debug,
		Trace:        trace,
	}
}

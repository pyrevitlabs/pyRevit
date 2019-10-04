package cli

import (
	"os"

	"github.com/docopt/docopt-go"
)

type Options struct {
	Version      string `json:"version"`
	Opts         *docopt.Opts
	ConnString   string `json:"connection_string"`
	ScriptsTable string `json:"script_table"`
	EventsTable  string `json:"events_table"`
	Port         int    `json:"server_port"`
	Debug        bool   `json:"debug_mode"`
	Trace        bool   `json:"trace_mode"`
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
		Version:      version,
		Opts:         &opts,
		ConnString:   connString,
		ScriptsTable: scriptTable,
		EventsTable:  eventTable,
		Port:         port,
		Debug:        debug,
		Trace:        trace,
	}
}

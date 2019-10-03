package cli

import (
	"os"
	"path/filepath"
	"strings"

	"github.com/docopt/docopt-go"
)

type Options struct {
	ExeName      string `json:"exe_name"`
	Version      string `json:"version"`
	Opts         *docopt.Opts
	ConnString   string `json:"connection_string"`
	ScriptsTable string `json:"script_table"`
	EventsTable  string `json:"events_table"`
	Port         int    `json:"server_port"`
	Https        bool   `json:"https"`
	Debug        bool   `json:"debug_mode"`
	Trace        bool   `json:"trace_mode"`
}

func getExeName() string {
	return strings.TrimSuffix(
		filepath.Base(os.Args[0]),
		filepath.Ext(os.Args[0]),
	)
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
	https, _ := opts.Bool("--https")

	debug, _ := opts.Bool("--debug")
	trace, _ := opts.Bool("--trace")

	return &Options{
		ExeName:      getExeName(),
		Version:      version,
		Opts:         &opts,
		ConnString:   connString,
		ScriptsTable: scriptTable,
		EventsTable:  eventTable,
		Port:         port,
		Https:        https,
		Debug:        debug,
		Trace:        trace,
	}
}

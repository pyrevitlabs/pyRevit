package cli

import (
	"os"

	"github.com/docopt/docopt-go"
)

type Options struct {
	Opts       *docopt.Opts
	ConnString string
	Table      string
	Port       int
	Debug      bool
	Trace      bool
}

func NewOptions() *Options {
	argv := os.Args[1:]

	parser := &docopt.Parser{
		HelpHandler: printHelpAndExit,
	}

	opts, _ := parser.ParseArgs(help, argv, version)

	connString, _ := opts.String("<db_uri>")
	table, _ := opts.String("<table>")
	port, _ := opts.Int("--port")

	debug, _ := opts.Bool("--debug")
	trace, _ := opts.Bool("--trace")

	return &Options{
		Opts:       &opts,
		ConnString: connString,
		Table:      table,
		Port:       port,
		Debug:      debug,
		Trace:      trace,
	}
}

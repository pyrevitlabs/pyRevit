package cli

import (
	"log"

	"pkg.re/essentialkaos/ek.v10/fmtc"
)

type Logger struct {
	PrintDebug bool
	PrintTrace bool
}

func NewLogger(options *Options) *Logger {
	return &Logger{
		PrintDebug: options.Debug,
		PrintTrace: options.Trace,
	}
}

func (m *Logger) Fatal(args ...interface{}) {
	log.Fatal(args...)
}

func (m *Logger) Debug(args ...interface{}) {
	if m.PrintDebug {
		log.Print(args...)
	}
}

func (m *Logger) Trace(args ...interface{}) {
	if m.PrintTrace {
		log.Print(args...)
	}
}

func (m *Logger) Print(args ...interface{}) {
	fmtc.Println(args...)
}

package persistence

import (
	"fmt"
	"time"

	"../cli"
)

var OkMessage = "[ {g}OK{!} ]"

type LogMeta struct {
	// for initial schema, the value will be ""; there is no 1.0
	SchemaVersion string `json:"schema" bson:"schema"` // schema 2.0
}

type EngineInfo struct {
	Type     string   `json:"type" bson:"type"` // schema 2.0
	Version  string   `json:"version" bson:"version"`
	SysPaths []string `json:"syspath" bson:"syspath"`
}

type TraceInfo struct {
	EngineInfo          EngineInfo `json:"engine" bson:"engine"`
	IronPythonTraceDump string     `json:"ipy" bson:"ipy"`         // initial schema
	CLRTraceDump        string     `json:"clr" bson:"clr"`         // initial schema
	Message             string     `json:"message" bson:"message"` // schema 2.0
}

type ScriptTelemetryRecord struct {
	LogMeta           LogMeta           `json:"meta" bson:"meta"`           // schema 2.0
	Date              string            `json:"date" bson:"date"`           // initial schema
	Time              string            `json:"time" bson:"time"`           // initial schema
	TimeStamp         string            `json:"timestamp" bson:"timestamp"` // schema 2.0
	UserName          string            `json:"username" bson:"username"`
	RevitVersion      string            `json:"revit" bson:"revit"`
	RevitBuild        string            `json:"revitbuild" bson:"revitbuild"`
	SessionId         string            `json:"sessionid" bson:"sessionid"`
	PyRevitVersion    string            `json:"pyrevit" bson:"pyrevit"`
	Clone             string            `json:"clone" bson:"clone"` // schema 2.0
	IsDebugMode       bool              `json:"debug" bson:"debug"`
	IsConfigMode      bool              `json:"config" bson:"config"`
	IsExecFromGUI     bool              `json:"from_gui" bson:"from_gui"`       // schema 2.0
	EngineCfgs        map[string]string `json:"engine_cfgs" bson:"engine_cfgs"` // schema 2.0
	CommandName       string            `json:"commandname" bson:"commandname"`
	CommandUniqueName string            `json:"commanduniquename" bson:"commanduniquename"`
	BundleName        string            `json:"commandbundle" bson:"commandbundle"`
	ExtensionName     string            `json:"commandextension" bson:"commandextension"`
	DocumentName      string            `json:"docname" bson:"docname"` // schema 2.0
	DocumentPath      string            `json:"docpath" bson:"docpath"` // schema 2.0
	ResultCode        int               `json:"resultcode" bson:"resultcode"`
	CommandResults    map[string]string `json:"commandresults" bson:"commandresults"`
	ScriptPath        string            `json:"scriptpath" bson:"scriptpath"`
	TraceInfo         TraceInfo         `json:"trace" bson:"trace"`
}

func (logrec ScriptTelemetryRecord) PrintRecordInfo(logger *cli.Logger, message string) {
	if logrec.LogMeta.SchemaVersion == "" {
		logger.Print(fmt.Sprintf(
			"%s %s-%s %q @ %s:%s [%s.%s] code=%d info=%v",
			message,
			logrec.Date,
			logrec.Time,
			logrec.UserName,
			logrec.RevitBuild,
			logrec.TraceInfo.EngineInfo.Version,
			logrec.ExtensionName,
			logrec.CommandName,
			logrec.ResultCode,
			logrec.CommandResults,
		))
	} else if logrec.LogMeta.SchemaVersion == "2.0" {
		logger.Print(fmt.Sprintf(
			"%s %s %q %s:%s (%s) [%s.%s] code=%d info=%v",
			message,
			logrec.TimeStamp,
			logrec.UserName,
			logrec.RevitBuild,
			logrec.TraceInfo.EngineInfo.Version,
			logrec.TraceInfo.EngineInfo.Type,
			logrec.ExtensionName,
			logrec.CommandName,
			logrec.ResultCode,
			logrec.CommandResults,
		))
	}
}

func (logrec ScriptTelemetryRecord) PrintOKRecordInfo(logger *cli.Logger) {
	logrec.PrintRecordInfo(logger, OkMessage)
}

func (logrec ScriptTelemetryRecord) UpdateTimeStamp() {
	// todo: validate by schema version
	if logrec.LogMeta.SchemaVersion == "2.0" {
		timeStamp, parseErr := time.Parse(time.RFC3339, logrec.TimeStamp)
		if parseErr != nil {
			logrec.Date = timeStamp.Format("2006-01-02")
			logrec.Time = timeStamp.Format("15:04:05")
		}
	}
}

func (logrec ScriptTelemetryRecord) Validate() {
	// todo: validate by schema version
	if logrec.LogMeta.SchemaVersion == "" {
	} else if logrec.LogMeta.SchemaVersion == "2.0" {
	}
}

type EventTelemetryRecord struct {
	LogMeta      LogMeta                `json:"meta" bson:"meta"`             // schema 2.0
	TimeStamp    string                 `json:"timestamp" bson:"timestamp"`   // schema 2.0
	EventType    string                 `json:"type" bson:"type"`             // schema 2.0
	EventArgs    map[string]interface{} `json:"args" bson:"args"`             // schema 2.0
	UserName     string                 `json:"username" bson:"username"`     // schema 2.0
	HostUserName string                 `json:"host_user" bson:"host_user"`   // schema 2.0
	RevitVersion string                 `json:"revit" bson:"revit"`           // schema 2.0
	RevitBuild   string                 `json:"revitbuild" bson:"revitbuild"` // schema 2.0

	// general
	Cancellable      bool   `json:"cancellable" bson:"cancellable"` // schema 2.0
	Cancelled        bool   `json:"cancelled" bson:"cancelled"`     // schema 2.0
	DocumentId       int    `json:"docid" bson:"docid"`             // schema 2.0
	DocumentType     string `json:"doctype" bson:"doctype"`         // schema 2.0
	DocumentTemplate string `json:"doctemplate" bson:"doctemplate"` // schema 2.0
	DocumentName     string `json:"docname" bson:"docname"`         // schema 2.0
	DocumentPath     string `json:"docpath" bson:"docpath"`         // schema 2.0
	ProjectNumber    string `json:"projectnum" bson:"projectnum"`   // schema 2.0
	ProjectName      string `json:"projectname" bson:"projectname"` // schema 2.0
}

func (logrec EventTelemetryRecord) PrintRecordInfo(logger *cli.Logger, message string) {
	if logrec.LogMeta.SchemaVersion == "2.0" {
		logger.Print(fmt.Sprintf(
			"%s %s [%s] %q @ %s doc=%q @ %s",
			message,
			logrec.TimeStamp,
			logrec.EventType,
			logrec.HostUserName,
			logrec.RevitBuild,
			logrec.DocumentName,
			logrec.DocumentPath,
		))
	}
}

func (logrec EventTelemetryRecord) PrintOKRecordInfo(logger *cli.Logger) {
	logrec.PrintRecordInfo(logger, OkMessage)
}

func (logrec EventTelemetryRecord) Validate() {
	// todo: validate by schema version
	if logrec.LogMeta.SchemaVersion == "2.0" {
	}
}

package persistence

import (
	"fmt"

	"pyrevittelemetryserver/cli"

	"github.com/asaskevich/govalidator"
)

// v1.0
type EngineInfoV1 struct {
	Version  string   `json:"version" bson:"version" valid:"-"`
	SysPaths []string `json:"syspath" bson:"syspath" valid:"-"`
}

type TraceInfoV1 struct {
	EngineInfo          EngineInfoV1 `json:"engine" bson:"engine" valid:"-"`
	IronPythonTraceDump string       `json:"ipy" bson:"ipy" valid:"-"`
	CLRTraceDump        string       `json:"clr" bson:"clr" valid:"-"`
}

type ScriptTelemetryRecordV1 struct {
	Date              string            `json:"date" bson:"date" valid:"-"`
	Time              string            `json:"time" bson:"time" valid:"-"`
	UserName          string            `json:"username" bson:"username" valid:"-"`
	RevitVersion      string            `json:"revit" bson:"revit" valid:"numeric~Invalid revit version"`
	RevitBuild        string            `json:"revitbuild" bson:"revitbuild" valid:"matches(\\d{8}_\\d{4}\\(x\\d{2}\\))~Invalid revit build number"`
	SessionId         string            `json:"sessionid" bson:"sessionid" valid:"uuidv4~Invalid session id"`
	PyRevitVersion    string            `json:"pyrevit" bson:"pyrevit" valid:"-"`
	IsDebugMode       bool              `json:"debug" bson:"debug"`
	IsConfigMode      bool              `json:"config" bson:"config"`
	CommandName       string            `json:"commandname" bson:"commandname" valid:"-"`
	CommandUniqueName string            `json:"commanduniquename" bson:"commanduniquename" valid:"-"`
	BundleName        string            `json:"commandbundle" bson:"commandbundle" valid:"-"`
	ExtensionName     string            `json:"commandextension" bson:"commandextension" valid:"-"`
	ResultCode        int               `json:"resultcode" bson:"resultcode" valid:"numeric~Invalid result code"`
	CommandResults    map[string]string `json:"commandresults" bson:"commandresults" valid:"-"`
	ScriptPath        string            `json:"scriptpath" bson:"scriptpath" valid:"-"`
	TraceInfo         TraceInfoV1       `json:"trace" bson:"trace"`
}

func (logrec ScriptTelemetryRecordV1) PrintRecordInfo(logger *cli.Logger, message string) {
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
}

func (logrec ScriptTelemetryRecordV1) Validate() error {
	// govalidator.SetFieldsRequiredByDefault(true)

	// validate now
	_, err := govalidator.ValidateStruct(logrec)
	return err
}

// v2.0
type EngineInfoV2 struct {
	Type     string                 `json:"type" bson:"type" valid:"engine~Invalid executor engine type"`
	Version  string                 `json:"version" bson:"version" valid:"-"`
	SysPaths []string               `json:"syspath" bson:"syspath" valid:"-"`
	Configs  map[string]interface{} `json:"configs" bson:"configs" valid:"-"`
}

type TraceInfoV2 struct {
	EngineInfo EngineInfoV2 `json:"engine" bson:"engine"`
	Message    string       `json:"message" bson:"message" valid:"-"`
}

type RecordMetaV2 struct {
	SchemaVersion string `json:"schema" bson:"schema" valid:"schema~Invalid schema version"`
}

type ScriptTelemetryRecordV2 struct {
	RecordMeta        RecordMetaV2           `json:"meta" bson:"meta"`
	TimeStamp         string                 `json:"timestamp" bson:"timestamp" valid:"rfc3339~Invalid timestamp"`
	UserName          string                 `json:"username" bson:"username" valid:"-"`
	HostUserName      string                 `json:"host_user" bson:"host_user" valid:"-"`
	RevitVersion      string                 `json:"revit" bson:"revit" valid:"numeric~Invalid revit version"`
	RevitBuild        string                 `json:"revitbuild" bson:"revitbuild" valid:"matches(\\d{8}_\\d{4}\\(x\\d{2}\\))~Invalid revit build number"`
	SessionId         string                 `json:"sessionid" bson:"sessionid" valid:"uuidv4~Invalid session id"`
	PyRevitVersion    string                 `json:"pyrevit" bson:"pyrevit" valid:"-"`
	Clone             string                 `json:"clone" bson:"clone" valid:"-"`
	IsDebugMode       bool                   `json:"debug" bson:"debug"`
	IsConfigMode      bool                   `json:"config" bson:"config"`
	IsExecFromGUI     bool                   `json:"from_gui" bson:"from_gui"`
	ExecId            string                 `json:"exec_id" bson:"exec_id" valid:"-"`
	ExecTimeStamp     string                 `json:"exec_timestamp" bson:"exec_timestamp" valid:"-"`
	CommandName       string                 `json:"commandname" bson:"commandname" valid:"-"`
	CommandUniqueName string                 `json:"commanduniquename" bson:"commanduniquename" valid:"-"`
	BundleName        string                 `json:"commandbundle" bson:"commandbundle" valid:"-"`
	ExtensionName     string                 `json:"commandextension" bson:"commandextension" valid:"-"`
	DocumentName      string                 `json:"docname" bson:"docname" valid:"-"`
	DocumentPath      string                 `json:"docpath" bson:"docpath" valid:"-"`
	ResultCode        int                    `json:"resultcode" bson:"resultcode" valid:"numeric~Invalid result code"`
	CommandResults    map[string]interface{} `json:"commandresults" bson:"commandresults" valid:"-"`
	ScriptPath        string                 `json:"scriptpath" bson:"scriptpath" valid:"-"`
	TraceInfo         TraceInfoV2            `json:"trace" bson:"trace"`
}

func (logrec ScriptTelemetryRecordV2) PrintRecordInfo(logger *cli.Logger, message string) {
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

func (logrec ScriptTelemetryRecordV2) Validate() error {
	// govalidator.SetFieldsRequiredByDefault(true)

	// custom validators
	govalidator.TagMap["schema"] = govalidator.Validator(func(str string) bool {
		return str == "2.0"
	})

	govalidator.TagMap["engine"] = govalidator.Validator(func(str string) bool {
		switch str {
		case
			"unknown",
			"ironpython",
			"cpython",
			"csharp",
			"invoke",
			"visualbasic",
			"ironruby",
			"dynamobim",
			"grasshopper",
			"content",
			"hyperlink":
			return true
		}
		return false
	})

	// validate now
	_, err := govalidator.ValidateStruct(logrec)
	return err
}

// introduced with api v2
type EventTelemetryRecordV2 struct {
	RecordMeta   RecordMetaV2           `json:"meta" bson:"meta"`
	TimeStamp    string                 `json:"timestamp" bson:"timestamp" valid:"rfc3339~Invalid timestamp"`
	HandlerId    string                 `json:"handler_id" bson:"handler_id" valid:"-"`
	EventType    string                 `json:"type" bson:"type" valid:"-"`
	EventArgs    map[string]interface{} `json:"args" bson:"args" valid:"-"`
	UserName     string                 `json:"username" bson:"username" valid:"-"`
	HostUserName string                 `json:"host_user" bson:"host_user" valid:"-"`
	RevitVersion string                 `json:"revit" bson:"revit" valid:"numeric~Invalid revit version"`
	RevitBuild   string                 `json:"revitbuild" bson:"revitbuild" valid:"matches(\\d{8}_\\d{4}\\(x\\d{2}\\))~Invalid revit build number"`

	// general
	Cancellable      bool   `json:"cancellable" bson:"cancellable"`
	Cancelled        bool   `json:"cancelled" bson:"cancelled"`
	DocumentId       int    `json:"docid" bson:"docid" valid:"-"`
	DocumentType     string `json:"doctype" bson:"doctype" valid:"-"`
	DocumentTemplate string `json:"doctemplate" bson:"doctemplate" valid:"-"`
	DocumentName     string `json:"docname" bson:"docname" valid:"-"`
	DocumentPath     string `json:"docpath" bson:"docpath" valid:"-"`
	ProjectNumber    string `json:"projectnum" bson:"projectnum" valid:"-"`
	ProjectName      string `json:"projectname" bson:"projectname" valid:"-"`
}

func (logrec EventTelemetryRecordV2) PrintRecordInfo(logger *cli.Logger, message string) {
	if logrec.RecordMeta.SchemaVersion == "2.0" {
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

func (logrec EventTelemetryRecordV2) Validate() error {
	// govalidator.SetFieldsRequiredByDefault(true)

	// custom validators
	govalidator.TagMap["schema"] = govalidator.Validator(func(str string) bool {
		return str == "2.0"
	})

	_, err := govalidator.ValidateStruct(logrec)
	return err
}

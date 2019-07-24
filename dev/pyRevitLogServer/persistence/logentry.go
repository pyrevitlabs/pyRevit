package persistence

type LogMeta struct {
	// for initial schema, the value will be ""; there is no 1.0
	SchemaVersion string `json:"schema"` // schema 2.0
}

type EngineInfo struct {
	Type     string   `json:"type"` // schema 2.0
	Version  string   `json:"version"`
	SysPaths []string `json:"syspath"`
}

type TraceInfo struct {
	EngineInfo          EngineInfo `json:"engine"`
	IronPythonTraceDump string     `json:"ipy"`     // initial schema
	CLRTraceDump        string     `json:"clr"`     // initial schema
	Message             string     `json:"message"` // schema 2.0
}

type LogRecord struct {
	LogMeta           LogMeta           `json:"meta"`      // schema 2.0
	Date              string            `json:"date"`      // initial schema
	Time              string            `json:"time"`      // initial schema
	TimeStamp         string            `json:"timestamp"` // schema 2.0
	UserName          string            `json:"username"`
	RevitVersion      string            `json:"revit"`
	RevitBuild        string            `json:"revitbuild"`
	SessionId         string            `json:"sessionid"`
	PyRevitVersion    string            `json:"pyrevit"`
	IsDebugMode       bool              `json:"debug"`
	IsAlternateMode   bool              `json:"alternate"`
	CommandName       string            `json:"commandname"`
	CommandUniqueName string            `json:"commanduniquename"`
	BundleName        string            `json:"commandbundle"`
	ExtensionName     string            `json:"commandextension"`
	ResultCode        int               `json:"resultcode"`
	CommandResults    map[string]string `json:"commandresults"`
	ScriptPath        string            `json:"scriptpath"`
	TraceInfo         TraceInfo         `json:"trace"`
}

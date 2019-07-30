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
	LogMeta              LogMeta           `json:"meta"`      // schema 2.0
	Date                 string            `json:"date"`      // initial schema
	Time                 string            `json:"time"`      // initial schema
	TimeStamp            string            `json:"timestamp"` // schema 2.0
	UserName             string            `json:"username"`
	RevitVersion         string            `json:"revit"`
	RevitBuild           string            `json:"revitbuild"`
	SessionId            string            `json:"sessionid"`
	PyRevitVersion       string            `json:"pyrevit"`
	Clone                string            `json:"clone"` // schema 2.0
	IsDebugMode          bool              `json:"debug"`
	IsConfigMode         bool              `json:"config"`
	IsExecFromGUI        bool              `json:"from_gui"`         // schema 2.0
	NeedsCleanEngine     bool              `json:"clean_engine"`     // schema 2.0
	NeedsFullFrameEngine bool              `json:"fullframe_engine"` // schema 2.0
	CommandName          string            `json:"commandname"`
	CommandUniqueName    string            `json:"commanduniquename"`
	BundleName           string            `json:"commandbundle"`
	ExtensionName        string            `json:"commandextension"`
	DocumentName         string            `json:"docname"` // schema 2.0
	DocumentPath         string            `json:"docpath"` // schema 2.0
	ResultCode           int               `json:"resultcode"`
	CommandResults       map[string]string `json:"commandresults"`
	ScriptPath           string            `json:"scriptpath"`
	TraceInfo            TraceInfo         `json:"trace"`
}

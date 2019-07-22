package persistence

type EngineInfo struct {
	Version  string   `json:"version"`
	SysPaths []string `json:"syspath"`
}

type TraceInfo struct {
	EngineInfo          EngineInfo `json:"engine"`
	IronPythonTraceDump string     `json:"ipy"`
	CLRTraceDump        string     `json:"clr"`
}

type LogRecord struct {
	Date              string            `json:"date"`
	Time              string            `json:"time"`
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

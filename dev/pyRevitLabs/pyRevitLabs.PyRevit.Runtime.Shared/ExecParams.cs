namespace pyRevitLabs.PyRevit.Runtime.Shared
{
    public class ExecParams
    {
        public string ExecId { get; }

        public string ExecTimeStamp { get; }

        public string ScriptPath { get; }

        public string ConfigScriptPath { get; }

        public string CommandUniqueId { get; }

        public string CommandControlId { get; }

        public string CommandName { get; }

        public string CommandBundle { get; }

        public string CommandExtension { get; }

        public string HelpSource { get; }

        public bool RefreshEngine { get; }

        public bool ConfigMode { get; }

        public bool DebugMode { get; }

        public bool ExecutedFromUI { get; }

        public object UIButton { get; }

        public ExecParams(string execId,
                          string execTimeStamp,
                          string scriptPath,
                          string configScriptPath,
                          string commandUniqueId,
                          string commandControlId,
                          string commandName,
                          string commandBundle,
                          string commandExtension,
                          string helpSource,
                          bool refreshEngine,
                          bool configMode,
                          bool debugMode,
                          bool executedFromUI,
                          object uiButton)
        {
            ExecId = execId;
            ExecTimeStamp = execTimeStamp;
            ScriptPath = scriptPath;
            ConfigScriptPath = configScriptPath;
            CommandUniqueId = commandUniqueId;
            CommandControlId = commandControlId;
            CommandName = commandName;
            CommandBundle = commandBundle;
            CommandExtension = commandExtension;
            HelpSource = helpSource;
            RefreshEngine = refreshEngine;
            ConfigMode = configMode;
            DebugMode = debugMode;
            ExecutedFromUI = executedFromUI;
            UIButton = uiButton;
        }
    }
}
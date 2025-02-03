namespace PyRevitLabs.PyRevit.Runtime {
    public class ScriptData {
        public string ScriptPath { get; set; }
        public string ConfigScriptPath { get; set; }
        public string CommandUniqueId { get; set; }
        public string CommandControlId { get; set; }
        public string CommandName { get; set; }
        public string CommandBundle { get; set; }
        public string CommandExtension { get; set; }
        public string CommandContext { get; set; }

        public string HelpSource { get; set; }
        public string Tooltip { get; set; }
    }
}
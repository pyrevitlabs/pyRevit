namespace pyRevitAssemblyBuilder.Shared
{
    public enum CommandComponentType
    {
        Unknown,
        Tab,
        Panel,
        PushButton,
        PullDown,
        SplitButton,
        SplitPushButton,
        Stack,
        SmartButton,
        PanelButton,
        LinkButton,
        InvokeButton,
        UrlButton,
        ContentButton,
        NoButton
    }

    public static class CommandComponentTypeExtensions
    {
        public static CommandComponentType FromExtension(string ext)
        {
            switch (ext.ToLowerInvariant())
            {
                case ".tab": return CommandComponentType.Tab;
                case ".panel": return CommandComponentType.Panel;
                case ".pushbutton": return CommandComponentType.PushButton;
                case ".pulldown": return CommandComponentType.PullDown;
                case ".splitbutton": return CommandComponentType.SplitButton;
                case ".splitpushbutton": return CommandComponentType.SplitPushButton;
                case ".stack": return CommandComponentType.Stack;
                case ".smartbutton": return CommandComponentType.SmartButton;
                case ".panelbutton": return CommandComponentType.PanelButton;
                case ".linkbutton": return CommandComponentType.LinkButton;
                case ".invokebutton": return CommandComponentType.InvokeButton;
                case ".urlbutton": return CommandComponentType.UrlButton;
                case ".content": return CommandComponentType.ContentButton;
                case ".nobutton": return CommandComponentType.NoButton;
                default: return CommandComponentType.Unknown;
            }
        }

        public static string ToExtension(this CommandComponentType type)
        {
            switch (type)
            {
                case CommandComponentType.Tab: return ".tab";
                case CommandComponentType.Panel: return ".panel";
                case CommandComponentType.PushButton: return ".pushbutton";
                case CommandComponentType.PullDown: return ".pulldown";
                case CommandComponentType.SplitButton: return ".splitbutton";
                case CommandComponentType.SplitPushButton: return ".splitpushbutton";
                case CommandComponentType.Stack: return ".stack";
                case CommandComponentType.SmartButton: return ".smartbutton";
                case CommandComponentType.PanelButton: return ".panelbutton";
                case CommandComponentType.LinkButton: return ".linkbutton";
                case CommandComponentType.InvokeButton: return ".invokebutton";
                case CommandComponentType.UrlButton: return ".urlbutton";
                case CommandComponentType.ContentButton: return ".content";
                case CommandComponentType.NoButton: return ".nobutton";
                default: return string.Empty;
            }
        }
    }
}

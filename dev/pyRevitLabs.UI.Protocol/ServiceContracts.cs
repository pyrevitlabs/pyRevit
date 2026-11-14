using System.Runtime.Serialization;

namespace PyRevitLabs.UI.Protocol;

public static class UiServices
{
    public const string Output = "output";
}

public static class UiMethods
{
    public const string HostInfo = "host.info";

    public static class Output
    {
        public const string Create = "output.create";
        public const string Append = "output.append";
        public const string ReplaceBody = "output.replace_body";
        public const string Inject = "output.inject";
        public const string SetTitle = "output.set_title";
        public const string SetVisibility = "output.set_visibility";
        public const string SetBounds = "output.set_bounds";
        public const string SetResizable = "output.set_resizable";
        public const string Focus = "output.focus";
        public const string Close = "output.close";
        public const string Navigate = "output.navigate";
        public const string Progress = "output.progress";
        public const string Indeterminate = "output.indeterminate";
        public const string Log = "output.log";
        public const string GetHtml = "output.get_html";
        public const string GetText = "output.get_text";
        public const string ReadInput = "output.read_input";
        public const string Closed = "output.closed";
    }

    public static string GetService(string method)
    {
        if (string.IsNullOrWhiteSpace(method))
            return string.Empty;
        var separator = method.IndexOf('.');
        return separator > 0 ? method.Substring(0, separator) : method;
    }
}

[DataContract]
public sealed class UiOutputPayload
{
    [DataMember(Name = "windowId", EmitDefaultValue = false)]
    public string? WindowId { get; set; }

    [DataMember(Name = "title", EmitDefaultValue = false)]
    public string? Title { get; set; }

    [DataMember(Name = "html", EmitDefaultValue = false)]
    public string? Html { get; set; }
    [DataMember(Name = "target", EmitDefaultValue = false)]
    public string? Target { get; set; }

    [DataMember(Name = "url", EmitDefaultValue = false)]
    public string? Url { get; set; }

    [DataMember(Name = "value", EmitDefaultValue = false)]
    public string? Value { get; set; }

    [DataMember(Name = "inputMode", EmitDefaultValue = false)]
    public string? InputMode { get; set; }

    [DataMember(Name = "level", EmitDefaultValue = false)]
    public string? Level { get; set; }

    [DataMember(Name = "width", EmitDefaultValue = false)]
    public double? Width { get; set; }

    [DataMember(Name = "height", EmitDefaultValue = false)]
    public double? Height { get; set; }

    [DataMember(Name = "left", EmitDefaultValue = false)]
    public double? Left { get; set; }

    [DataMember(Name = "top", EmitDefaultValue = false)]
    public double? Top { get; set; }
    [DataMember(Name = "progressValue", EmitDefaultValue = false)]
    public double? ProgressValue { get; set; }

    [DataMember(Name = "progressMaximum", EmitDefaultValue = false)]
    public double? ProgressMaximum { get; set; }

    [DataMember(Name = "visible", EmitDefaultValue = false)]
    public bool? Visible { get; set; }

    [DataMember(Name = "resizable", EmitDefaultValue = false)]
    public bool? Resizable { get; set; }

    [DataMember(Name = "indeterminate", EmitDefaultValue = false)]
    public bool? Indeterminate { get; set; }
}

[DataContract]
public sealed class UiOutputResponsePayload
{
    [DataMember(Name = "ok")]
    public bool Ok { get; set; } = true;

    [DataMember(Name = "value", EmitDefaultValue = false)]
    public string? Value { get; set; }
}
[DataContract]
public sealed class UiEventPayload
{
    [DataMember(Name = "windowId")]
    public string WindowId { get; set; } = string.Empty;

    [DataMember(Name = "value", EmitDefaultValue = false)]
    public string? Value { get; set; }
}

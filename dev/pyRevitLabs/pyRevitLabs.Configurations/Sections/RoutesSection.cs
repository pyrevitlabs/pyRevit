using System.ComponentModel;
using pyRevitLabs.Configurations.Attributes;

namespace pyRevitLabs.Configurations.Sections;

[SectionName("routes")]
public sealed record RoutesSection
{
    [KeyName("enabled")]
    public bool? Status { get; set; }

    [KeyName("host")]
    public string? Host { get; set; }

    [KeyName("port")]
    [DefaultValue(48884)]
    public int? Port { get; set; }

    [KeyName("core_api")]
    public bool? LoadCoreApi { get; set; }
}

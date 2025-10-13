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
    public int? Port { get; set; } = 48884;
    
    [KeyName("core_api")]
    public bool? LoadCoreApi { get; set; }
}
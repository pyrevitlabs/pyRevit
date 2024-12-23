namespace pyRevitLabs.Configurations;

public sealed record RoutesSection
{
    public bool Status { get; set; }
    
    public string? Host { get; set; }
    public int Port { get; set; } = 48884;
    public bool LoadCoreApi { get; set; }
}
namespace pyRevitLabs.Configurations;

internal sealed record RoutesSection
{
    public bool Status { get; set; }
    public bool LoadCoreApi { get; set; }
    
    public string? Host { get; set; }
    public int Port { get; set; } = 48884;
}
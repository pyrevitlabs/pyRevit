namespace pyRevitLabs.Configurations;

internal sealed record ConfigurationName
{
    public int Index { get; set;  }
    public string? Name { get; set; }
}
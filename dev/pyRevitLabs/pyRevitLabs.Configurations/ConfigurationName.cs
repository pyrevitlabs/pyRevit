namespace pyRevitLabs.Configurations;

public sealed record ConfigurationName
{

    public required int Index { get; init;  }
    public required string Name { get; init; }
}
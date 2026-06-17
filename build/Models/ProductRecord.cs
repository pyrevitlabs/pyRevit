namespace Build.Models;

public sealed record ProductRecord(
    string Product,
    string Release,
    string Version,
    string Key);

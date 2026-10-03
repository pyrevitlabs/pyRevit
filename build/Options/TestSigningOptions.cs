namespace Build.Options;

public sealed class TestSigningOptions
{
    public string Fingerprint { get; set; } = string.Empty;

    public bool Local { get; set; }

    public bool RemoveCert { get; set; }
}

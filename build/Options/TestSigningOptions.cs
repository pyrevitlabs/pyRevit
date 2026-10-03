namespace Build.Options;

/// <summary>Settings for the test-only signing modes; never used by production signing.</summary>
public sealed class TestSigningOptions
{
    /// <summary>SHA-256 fingerprint of the certificate <c>sign-test</c> signs with.</summary>
    public string Fingerprint { get; set; } = string.Empty;

    public bool Local { get; set; }
}

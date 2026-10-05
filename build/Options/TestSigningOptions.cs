namespace Build.Options;

/// <summary>Settings for the test-only signing modes; never used by production signing.</summary>
public sealed class TestSigningOptions
{
    /// <summary>SHA-256 fingerprint of the certificate <c>sign-test</c> signs with.</summary>
    public string Fingerprint { get; set; } = string.Empty;

    /// <summary>Sign with the per-developer certificate instead of <see cref="Fingerprint"/>.</summary>
    /// <remarks>
    /// Never bound from configuration: <c>Program.cs</c> overwrites it from <c>PipelineModes</c> after
    /// <c>Bind</c>, so <c>TestSigning__Local=true</c> cannot switch it on. That <c>Configure</c> call must stay
    /// registered after the <c>Bind</c>.
    /// </remarks>
    public bool Local { get; set; }
}

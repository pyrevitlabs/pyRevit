namespace Build.Options;

public sealed class SigningOptions
{
    public string TenantId { get; set; } = string.Empty;

    public string ClientId { get; set; } = string.Empty;

    public string ClientSecret { get; set; } = string.Empty;

    public string Endpoint { get; set; } = string.Empty;

    public string SigningAccountName { get; set; } = string.Empty;

    public string CertificateProfileName { get; set; } = string.Empty;

    public bool IsConfigured =>
        !string.IsNullOrWhiteSpace(TenantId)
        && !string.IsNullOrWhiteSpace(ClientId)
        && !string.IsNullOrWhiteSpace(ClientSecret)
        && !string.IsNullOrWhiteSpace(Endpoint)
        && !string.IsNullOrWhiteSpace(SigningAccountName)
        && !string.IsNullOrWhiteSpace(CertificateProfileName);
}

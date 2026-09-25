namespace pyRevitLabs.Configurations.Security;

/// <summary>
/// Which of the two credential shapes an <see cref="ExtensionCredential.Secret"/>
/// is. Recorded in the stored blob so a reader can tell a token from a password
/// without inferring it from the username.
/// </summary>
public enum ExtensionCredentialKind {
    /// <summary>
    /// A personal access token. The username travels alongside it but is a
    /// convention of the host (GitHub expects <c>oauth2</c>, GitLab
    /// <c>x-access-token</c>), not an account the user chose.
    /// </summary>
    Token,

    /// <summary>
    /// A password belonging to a real account, as used for HTTP basic auth
    /// against self-hosted forges.
    /// </summary>
    Password
}

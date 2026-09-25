using System;
using System.Text;
using pyRevitLabs.Configurations.Security;

namespace pyRevitLabs.Configurations.Tests;

/// <summary>
/// Covers <see cref="ExtensionCredentialProtector"/>: the sealed value round-trips
/// to the same credential, the recorded kind survives, and every way a stored
/// blob can be unusable is reported as
/// <see cref="ExtensionCredentialUnavailableException"/> rather than as "no
/// credential configured".
/// </summary>
/// <remarks>
/// These tests seal and unseal real DPAPI blobs under the running user. On a
/// platform without DPAPI they fail loudly rather than skipping: the protector
/// has no cross-platform path, so a green run here means the Windows-only
/// assumption still holds.
/// </remarks>
public class ExtensionCredentialProtectorTests {
    private const string Token = "ghp_0123456789abcdefABCDEF0123456789abcdefAB";
    private const string Password = "correct horse battery staple";
    private const string Username = "oauth2";

    [Fact]
    public void ProtectThenUnprotect_RestoresTokenCredential() {
        var original = new ExtensionCredential(Username, Token, ExtensionCredentialKind.Token);

        ExtensionCredential restored = ExtensionCredentialProtector.Unprotect(
            ExtensionCredentialProtector.Protect(original));

        Assert.Equal(Username, restored.Username);
        Assert.Equal(Token, restored.Secret);
        Assert.Equal(ExtensionCredentialKind.Token, restored.Kind);
    }

    [Fact]
    public void ProtectThenUnprotect_RestoresPasswordCredential() {
        var original = new ExtensionCredential("alex", Password, ExtensionCredentialKind.Password);

        ExtensionCredential restored = ExtensionCredentialProtector.Unprotect(
            ExtensionCredentialProtector.Protect(original));

        Assert.Equal("alex", restored.Username);
        Assert.Equal(Password, restored.Secret);
        Assert.Equal(ExtensionCredentialKind.Password, restored.Kind);
    }

    /// <summary>
    /// The whole point of the format: the secret must not be recoverable by
    /// reading the config value. Base64 of the outer seal is checked because
    /// that is what actually lands in the INI file.
    /// </summary>
    [Fact]
    public void Protect_StoredValue_DoesNotContainTheSecret() {
        string stored = ExtensionCredentialProtector.Protect(
            new ExtensionCredential(Username, Token, ExtensionCredentialKind.Token));

        Assert.DoesNotContain(Token, stored, StringComparison.Ordinal);
        Assert.DoesNotContain(Username, Encoding.UTF8.GetString(Convert.FromBase64String(stored)),
            StringComparison.Ordinal);
    }

    /// <summary>
    /// A token is base64-shaped by nature, so an unencoded secret would leak
    /// through a naive base64 check. This pins that the payload is sealed, not
    /// merely encoded.
    /// </summary>
    [Fact]
    public void Protect_StoredValue_IsNotJustTheEncodedPayload() {
        string stored = ExtensionCredentialProtector.Protect(
            new ExtensionCredential(Username, Password, ExtensionCredentialKind.Password));

        string payload = $"{Convert.ToBase64String(Encoding.UTF8.GetBytes(Username))}.";
        Assert.DoesNotContain(payload, Encoding.UTF8.GetString(Convert.FromBase64String(stored)),
            StringComparison.Ordinal);
    }

    [Fact]
    public void Protect_SameInput_ProducesDifferentStoredValues() {
        var credential = new ExtensionCredential(Username, Token, ExtensionCredentialKind.Token);

        string first = ExtensionCredentialProtector.Protect(credential);
        string second = ExtensionCredentialProtector.Protect(credential);

        // DPAPI uses a fresh IV per call, so two seals of the same input differ.
        // This also means a value in the config is not a stable identifier.
        Assert.NotEqual(first, second);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void Protect_BlankUsername_Throws(string? username) {
        var credential = new ExtensionCredential(username!, Token, ExtensionCredentialKind.Token);

        Assert.Throws<ArgumentException>(() => ExtensionCredentialProtector.Protect(credential));
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public void Protect_BlankSecret_Throws(string secret) {
        var credential = new ExtensionCredential(Username, secret, ExtensionCredentialKind.Token);

        Assert.Throws<ArgumentException>(() => ExtensionCredentialProtector.Protect(credential));
    }

    [Fact]
    public void Protect_NullCredential_Throws() =>
        Assert.Throws<ArgumentNullException>(
            () => ExtensionCredentialProtector.Protect(null!));

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void Unprotect_NullOrBlank_ThrowsUnavailable(string? stored) =>
        Assert.Throws<ExtensionCredentialUnavailableException>(
            () => ExtensionCredentialProtector.Unprotect(stored));

    /// <summary>
    /// Not base64 at all: a config value a user edited by hand, or one written
    /// by a build that stored something else under this key.
    /// </summary>
    [Fact]
    public void Unprotect_NotBase64_ThrowsUnavailable() =>
        Assert.Throws<ExtensionCredentialUnavailableException>(
            () => ExtensionCredentialProtector.Unprotect("this is not a sealed blob"));

    /// <summary>
    /// Valid base64, but the bytes are not a DPAPI blob - the shape a value
    /// takes when something overwrote the key with unrelated content.
    /// </summary>
    [Fact]
    public void Unprotect_ValidBase64ButNotSealed_ThrowsUnavailable() =>
        Assert.Throws<ExtensionCredentialUnavailableException>(
            () => ExtensionCredentialProtector.Unprotect(
                Convert.ToBase64String(Encoding.UTF8.GetBytes("Y2FwdHVyZQ=="))));

    /// <summary>
    /// A real blob, truncated. A partially written config is a plausible way to
    /// end up here, and it must not be reported as an ordinary empty credential.
    /// </summary>
    [Fact]
    public void Unprotect_TruncatedBlob_ThrowsUnavailable() {
        string stored = ExtensionCredentialProtector.Protect(
            new ExtensionCredential(Username, Token, ExtensionCredentialKind.Token));
        string truncated = stored.Substring(0, stored.Length / 2);

        Assert.Throws<ExtensionCredentialUnavailableException>(
            () => ExtensionCredentialProtector.Unprotect(truncated));
    }

    /// <summary>
    /// Flipping one byte of a real blob: tampering must fail the DPAPI
    /// authentication check rather than yield different plaintext.
    /// </summary>
    [Fact]
    public void Unprotect_TamperedBlob_ThrowsUnavailable() {
        string stored = ExtensionCredentialProtector.Protect(
            new ExtensionCredential(Username, Token, ExtensionCredentialKind.Token));
        byte[] bytes = Convert.FromBase64String(stored);
        bytes[bytes.Length / 2] ^= 0xFF;

        Assert.Throws<ExtensionCredentialUnavailableException>(
            () => ExtensionCredentialProtector.Unprotect(Convert.ToBase64String(bytes)));
    }

    /// <summary>
    /// The documented consequence of a user-scope blob reaching another Windows
    /// profile. Simulated by sealing under pyRevit's entropy and reading it back
    /// as if it had been sealed with a different one, which is what a blob
    /// copied between profiles amounts to at the DPAPI boundary.
    /// </summary>
    [Fact]
    public void Unprotect_BlobSealedForOtherEntropy_ThrowsUnavailable() {
        string stored = ExtensionCredentialProtector.Protect(
            new ExtensionCredential(Username, Token, ExtensionCredentialKind.Token));
        // Re-seal the same plaintext under the same scope but a foreign entropy,
        // proving the entropy really is part of what is authenticated.
        string foreign = ResealUnderForeignEntropy(stored, "someone-elses-app.v1");

        Assert.Throws<ExtensionCredentialUnavailableException>(
            () => ExtensionCredentialProtector.Unprotect(foreign));
    }

    [Fact]
    public void TryUnprotect_ValidValue_ReturnsTrueAndCredential() {
        string stored = ExtensionCredentialProtector.Protect(
            new ExtensionCredential(Username, Token, ExtensionCredentialKind.Token));

        bool ok = ExtensionCredentialProtector.TryUnprotect(stored, out ExtensionCredential? credential);

        Assert.True(ok);
        Assert.NotNull(credential);
        Assert.Equal(Token, credential!.Secret);
    }

    /// <summary>
    /// The degrade path, which must yield null and never a partial credential.
    /// </summary>
    [Fact]
    public void TryUnprotect_UnusableValue_ReturnsFalseAndNull() {
        bool ok = ExtensionCredentialProtector.TryUnprotect("not a blob", out ExtensionCredential? credential);

        Assert.False(ok);
        Assert.Null(credential);
    }

    [Fact]
    public void Entropy_IsTheDocumentedContractValue() =>
        Assert.Equal("pyRevitLabs.ExtensionCredential.v1", ExtensionCredentialProtector.Entropy);

    /// <summary>
    /// Unseals with pyRevit's entropy and reseals under a different one, so a
    /// test can produce a blob that is genuinely sealed but for the wrong
    /// binding without depending on a second Windows account.
    /// </summary>
    private static string ResealUnderForeignEntropy(string stored, string foreignEntropy) {
        string payload = Dpapi.Unprotect(
            Convert.FromBase64String(stored),
            Encoding.UTF8.GetBytes(ExtensionCredentialProtector.Entropy),
            out _);

        return Convert.ToBase64String(
            Dpapi.Protect(payload, Encoding.UTF8.GetBytes(foreignEntropy), "foreign"));
    }
}

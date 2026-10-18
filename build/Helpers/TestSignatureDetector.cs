using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;

namespace Build.Helpers;

/// <summary>
/// The single definition of what a pyRevit test signature is, shared by the side that signs test builds and the
/// side that keeps them out of installers.
/// </summary>
/// <remarks>
/// Invariant: test signing only uses certificates <see cref="EnsureTestSigner"/> accepts, and packaging rejects every
/// file <see cref="FindTestSignedFiles"/> reports. Both go through <see cref="IsTestSigner"/>, so changing the subject
/// rule here changes both sides together.
/// </remarks>
public static class TestSignatureDetector {
    internal const string LocalSubjectPrefix = "CN=pyRevit Local Dev";
    internal const string CiSubjectPrefix = "CN=pyRevit CI Test";

    /// <summary>
    /// True when <paramref name="subject"/> names a pyRevit test certificate (local developer or CI throwaway).
    /// </summary>
    /// <remarks>
    /// An accident guard, not a security check: it prefix-matches a name anyone can put in a certificate CN.
    /// </remarks>
    internal static bool IsTestSigner(string? subject) =>
        subject is not null
        && (subject.StartsWith(LocalSubjectPrefix, StringComparison.OrdinalIgnoreCase)
            || subject.StartsWith(CiSubjectPrefix, StringComparison.OrdinalIgnoreCase));

    /// <summary>Refuses a signing certificate whose signatures packaging would not recognise as test signatures.</summary>
    /// <exception cref="InvalidOperationException">The subject is not a test subject.</exception>
    public static void EnsureTestSigner(X509Certificate2 certificate) {
        ArgumentNullException.ThrowIfNull(certificate);
        if (!IsTestSigner(certificate.Subject)) {
            throw new InvalidOperationException(
                $"Refusing to test-sign with '{certificate.Subject}': the subject must start with " +
                $"'{LocalSubjectPrefix}' or '{CiSubjectPrefix}' so packaging can detect and reject the signature.");
        }
    }

    /// <summary>
    /// Returns the files whose Authenticode signer is a test certificate. Unsigned files and files
    /// signed by any other identity are not reported.
    /// </summary>
    public static IReadOnlyList<string> FindTestSignedFiles(IEnumerable<string> files) =>
        files.Where(file => IsTestSigner(ReadSignerSubject(file))).ToList();

    /// <summary>Throws when any pyRevit binary under <paramref name="binPath"/> carries a test signature.</summary>
    /// <exception cref="InvalidOperationException">At least one test-signed binary was found.</exception>
    public static void EnsureNoTestSignedBinaries(string binPath) {
        var offenders = FindTestSignedFiles(SigningHelper.FindPyRevitBinaries(binPath));
        if (offenders.Count > 0) {
            throw new InvalidOperationException(
                $"{offenders.Count} binaries in bin/ are signed with a test certificate (first: {offenders[0]}). " +
                "Packaging needs unsigned binaries: rebuild them with 'ci', or in a pack job restore bin/ from " +
                "the unsigned-bin-<sha> artifact.");
        }
    }

    private static string? ReadSignerSubject(string file) {
        try {
#pragma warning disable SYSLIB0057
            using var certificate = X509Certificate.CreateFromSignedFile(file);
#pragma warning restore SYSLIB0057
            return certificate.Subject;
        }
        catch (CryptographicException) {
            return null;
        }
    }
}

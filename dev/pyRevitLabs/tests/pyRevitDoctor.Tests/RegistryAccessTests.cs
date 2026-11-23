using Microsoft.Win32;
using pyRevitDoctor;

namespace pyRevitDoctor.Tests;

/// <summary>
/// Coverage for opening the registry targets of <c>purge-installs</c>: an unreadable target must be
/// counted as a failure, not skipped silently. The opener is faked, only a read-only HKCU key is real.
/// </summary>
[Trait("Level", "Unit")]
[Trait("Environment", "HostFree")]
public class RegistryAccessTests {
    private const string Description = @"(LocalMachine)\SOFTWARE\Fake";

    private static (PurgeSession Session, StringWriter Output) NewSession(bool dryRun = false) {
        var output = new StringWriter();
        return (new PurgeSession(new PurgeOptions { DryRun = dryRun }, output), output);
    }

    private static RegistryKey ReadableKey() => Registry.CurrentUser.OpenSubKey("Software");

    [Fact]
    public void WriteDeniedButReadableTargetIsScannedReadOnly() {
        var (session, _) = NewSession();
        var requestedWritable = new List<bool>();

        using var key = RegistryAccess.TryOpenForPurge(session, Description, writable => {
            requestedWritable.Add(writable);
            return writable ? throw new UnauthorizedAccessException("denied") : ReadableKey();
        });

        Assert.NotNull(key);
        Assert.Equal(new[] { true, false }, requestedWritable);
        Assert.Equal(0, session.FailedCount);
    }

    [Fact]
    public void DryRunOpensReadOnlyWithoutTryingToWrite() {
        var (session, _) = NewSession(dryRun: true);
        var requestedWritable = new List<bool>();

        using var key = RegistryAccess.TryOpenForPurge(session, Description, writable => {
            requestedWritable.Add(writable);
            return ReadableKey();
        });

        Assert.NotNull(key);
        Assert.Equal(new[] { false }, requestedWritable);
    }

    [Theory]
    [InlineData(typeof(UnauthorizedAccessException))]
    [InlineData(typeof(System.Security.SecurityException))]
    public void UnreadableTargetIsReportedAsFailureWithAdminHint(Type exceptionType) {
        var (session, output) = NewSession();

        var key = RegistryAccess.TryOpenForPurge(session, Description, _ => throw (Exception)Activator.CreateInstance(exceptionType, "denied"));
        session.PrintSummary();

        Assert.Null(key);
        Assert.Equal(1, session.FailedCount);
        Assert.Contains("Error Opening " + Description, output.ToString());
        Assert.Contains("Run this command as admin", output.ToString());
    }

    [Fact]
    public void OtherOpenErrorsAreReportedAsFailures() {
        var (session, _) = NewSession();

        var key = RegistryAccess.TryOpenForPurge(session, Description, _ => throw new IOException("broken"));

        Assert.Null(key);
        Assert.Equal(1, session.FailedCount);
    }

    [Fact]
    public void MissingKeyIsSkippedWithoutFailure() {
        var (session, output) = NewSession();

        var key = RegistryAccess.TryOpenForPurge(session, Description, _ => null);

        Assert.Null(key);
        Assert.Equal(0, session.FailedCount);
        Assert.DoesNotContain("Error", output.ToString());
    }

    /// <summary>
    /// A failed target must not stop the scan: the next target still opens and the failure stays counted.
    /// </summary>
    [Fact]
    public void ScanContinuesAfterAnUnreadableTarget() {
        var (session, _) = NewSession();

        var unreadable = RegistryAccess.TryOpenForPurge(session, "first", _ => throw new UnauthorizedAccessException("denied"));
        using var readable = RegistryAccess.TryOpenForPurge(session, "second", _ => ReadableKey());

        Assert.Null(unreadable);
        Assert.NotNull(readable);
        Assert.Equal(1, session.FailedCount);
    }
}

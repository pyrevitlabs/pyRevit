using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class FileLockHelperTests
{
    [TestMethod]
    public void IsFileLocked_returns_false_for_missing_file()
    {
        Assert.IsFalse(FileLockHelper.IsFileLocked(Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".dll")));
    }

    [TestMethod]
    public void IsFileLocked_returns_true_when_file_is_open_exclusively()
    {
        var path = Path.Combine(Path.GetTempPath(), "pyrevit-lock-test-" + Guid.NewGuid().ToString("N") + ".dll");
        File.WriteAllBytes(path, [0x00]);

        try
        {
            using var stream = new FileStream(path, FileMode.Open, FileAccess.ReadWrite, FileShare.None);
            Assert.IsTrue(FileLockHelper.IsFileLocked(path));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [TestMethod]
    public void IsFileLocked_returns_false_for_unlocked_file()
    {
        var path = Path.Combine(Path.GetTempPath(), "pyrevit-lock-test-" + Guid.NewGuid().ToString("N") + ".dll");
        File.WriteAllBytes(path, [0x00]);

        try
        {
            Assert.IsFalse(FileLockHelper.IsFileLocked(path));
        }
        finally
        {
            File.Delete(path);
        }
    }
}

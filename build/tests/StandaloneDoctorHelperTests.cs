using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class StandaloneDoctorHelperTests
{
    private string _root = string.Empty;

    [TestInitialize]
    public void CreateRoot()
    {
        _root = Path.Combine(Path.GetTempPath(), "pyrevit-standalone-doctor-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_root);
    }

    [TestCleanup]
    public void DeleteRoot()
    {
        if (Directory.Exists(_root))
        {
            Directory.Delete(_root, recursive: true);
        }
    }

    [TestMethod]
    public void EnsureSingleFilePublish_accepts_an_executable_without_a_separate_assembly()
    {
        File.WriteAllText(Path.Combine(_root, "pyrevit-doctor.exe"), "bundle");
        File.WriteAllText(Path.Combine(_root, "pyrevit-doctor.pdb"), "symbols");

        StandaloneDoctorHelper.EnsureSingleFilePublish(_root);
    }

    [TestMethod]
    public void EnsureSingleFilePublish_rejects_an_executable_that_needs_its_assembly()
    {
        File.WriteAllText(Path.Combine(_root, "pyrevit-doctor.exe"), "host");
        File.WriteAllText(Path.Combine(_root, "pyrevit-doctor.dll"), "assembly");

        var error = Assert.ThrowsExactly<InvalidOperationException>(
            () => StandaloneDoctorHelper.EnsureSingleFilePublish(_root));

        StringAssert.Contains(error.Message, "PublishSingleFile");
    }

    [TestMethod]
    public void EnsureSingleFilePublish_rejects_output_without_the_executable()
    {
        Assert.ThrowsExactly<FileNotFoundException>(
            () => StandaloneDoctorHelper.EnsureSingleFilePublish(_root));
    }

    [TestMethod]
    public void StageForRelease_copies_the_executable_under_its_unversioned_name()
    {
        var binPath = Path.Combine(_root, "bin");
        var distPath = Path.Combine(_root, "dist");
        Directory.CreateDirectory(binPath);
        File.WriteAllText(Path.Combine(binPath, "pyrevit-doctor.exe"), "signed");

        var staged = StandaloneDoctorHelper.StageForRelease(binPath, distPath);

        Assert.AreEqual(Path.Combine(distPath, "pyrevit-doctor.exe"), staged);
        Assert.AreEqual("signed", File.ReadAllText(staged));
    }

    [TestMethod]
    public void StageForRelease_replaces_an_earlier_copy()
    {
        var binPath = Path.Combine(_root, "bin");
        var distPath = Path.Combine(_root, "dist");
        Directory.CreateDirectory(binPath);
        Directory.CreateDirectory(distPath);
        File.WriteAllText(Path.Combine(binPath, "pyrevit-doctor.exe"), "signed");
        File.WriteAllText(Path.Combine(distPath, "pyrevit-doctor.exe"), "unsigned");

        var staged = StandaloneDoctorHelper.StageForRelease(binPath, distPath);

        Assert.AreEqual("signed", File.ReadAllText(staged));
    }

    [TestMethod]
    public void StageForRelease_fails_when_bin_has_no_doctor()
    {
        var binPath = Path.Combine(_root, "bin");
        Directory.CreateDirectory(binPath);

        Assert.ThrowsExactly<FileNotFoundException>(
            () => StandaloneDoctorHelper.StageForRelease(binPath, Path.Combine(_root, "dist")));
    }
}

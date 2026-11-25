using pyRevitAssemblyBuilder.SessionManager;
using NUnit.Framework;

namespace pyRevitAssemblyBuilder.Tests
{
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class AppDataCleanupTests
    {
        [TestCase("pyRevit_2025_14422_mydata.tmp", 14422)]
        [TestCase("pyRevit_2025_14422_SectionBoxTemp.tmp", 14422)]
        [TestCase("pyRevit_2025_14422_routes.pickle", 14422)]
        [TestCase("pyRevit_2025_1234_sync_55_views.tmp", 1234)]
        public void TryGetInstanceFilePid_InstanceFile_ReturnsOwningPid(string fileName, int expectedPid)
        {
            var result = SessionManagerService.TryGetInstanceFilePid(fileName, out var pid);

            Assert.That(result, Is.True);
            Assert.That(pid, Is.EqualTo(expectedPid));
        }

        [TestCase("pyRevit_2025_Highlighted Rows_K20V001_2025_user.pym")]
        [TestCase("pyRevit_2025_Highlighted Rows_K-20-V-001_2025.pym")]
        [TestCase("pyRevit_2025_data_Project_123_Plan.pym")]
        [TestCase("pyRevit_2025_user_14422_legacy.tmp")]
        [TestCase("pyRevit_user_config.ini")]
        [TestCase("pyRevit_config.ini")]
        public void TryGetInstanceFilePid_NonInstanceFile_ReturnsFalse(string fileName)
        {
            var result = SessionManagerService.TryGetInstanceFilePid(fileName, out _);

            Assert.That(result, Is.False);
        }
    }
}

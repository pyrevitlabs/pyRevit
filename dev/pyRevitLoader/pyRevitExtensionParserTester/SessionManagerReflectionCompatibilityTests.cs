using pyRevitAssemblyBuilder.SessionManager;
using NUnit.Framework;

namespace pyRevitExtensionParserTester
{
    [TestFixture]
    public class SessionManagerReflectionCompatibilityTests
    {
        private class ConfigWithProperty
        {
            public bool SharedSessionEngine { get; set; }
        }

        private class ConfigWithoutMember
        {
            public bool RefreshEngine { get; set; }
        }

        [Test]
        public void TrySetMemberValue_SetsExistingMember()
        {
            var config = new ConfigWithProperty();

            var result = SessionManagerService.TrySetMemberValue(
                typeof(ConfigWithProperty),
                config,
                "SharedSessionEngine",
                true);

            Assert.That(result, Is.True);
            Assert.That(config.SharedSessionEngine, Is.True);
        }

        [Test]
        public void TrySetMemberValue_MissingMember_ReturnsFalse()
        {
            var config = new ConfigWithoutMember();

            var result = SessionManagerService.TrySetMemberValue(
                typeof(ConfigWithoutMember),
                config,
                "SharedSessionEngine",
                true);

            Assert.That(result, Is.False);
            Assert.That(config.RefreshEngine, Is.False);
        }
    }
}

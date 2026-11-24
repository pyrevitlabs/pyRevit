using System;
using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    /// <summary>Generated identifiers retain the portable Base64 GUID format.</summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class IdentifierTests {
        /// <summary>Consumers can decode an identifier into a nonempty GUID.</summary>
        [Test]
        public void NewShortUUID_RoundTripsAsGuid() {
            var identifier = CommonUtils.NewShortUUID();

            var decoded = new Guid(Convert.FromBase64String(identifier));

            Assert.That(decoded, Is.Not.EqualTo(Guid.Empty));
        }
    }
}

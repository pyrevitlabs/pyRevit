using System;

using NUnit.Framework;

using PyRevitLoader;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// A session load releases what the previous session load registered under the same slot.
    /// </summary>
    [TestFixture]
    [NonParallelizable]
    [Category("HostFree")]
    [Category("Unit")]
    public class SessionResourceRegistryTests
    {
        private string _slot;

        [SetUp]
        public void SetUp()
        {
            _slot = "slot-" + Guid.NewGuid().ToString("N");
        }

        [Test]
        public void Replace_FirstRegistration_ReleasesNothing()
        {
            var released = 0;

            SessionResourceRegistry.Replace(_slot, () => released++);

            Assert.That(released, Is.EqualTo(0));
        }

        [Test]
        public void Replace_SecondRegistration_ReleasesOnlyThePreviousOne()
        {
            var first = 0;
            var second = 0;
            SessionResourceRegistry.Replace(_slot, () => first++);

            SessionResourceRegistry.Replace(_slot, () => second++);

            Assert.That(first, Is.EqualTo(1));
            Assert.That(second, Is.EqualTo(0));
        }

        [Test]
        public void Replace_ReleasesEachPreviousOnlyOnce()
        {
            var first = 0;
            SessionResourceRegistry.Replace(_slot, () => first++);
            SessionResourceRegistry.Replace(_slot, () => { });

            SessionResourceRegistry.Replace(_slot, () => { });

            Assert.That(first, Is.EqualTo(1));
        }

        [Test]
        public void Replace_DifferentSlots_AreIndependent()
        {
            var released = 0;
            SessionResourceRegistry.Replace(_slot + "a", () => released++);

            SessionResourceRegistry.Replace(_slot + "b", () => { });

            Assert.That(released, Is.EqualTo(0));
        }

        [Test]
        public void Replace_FailingPreviousRelease_DoesNotThrowAndStillStoresNew()
        {
            var second = 0;
            SessionResourceRegistry.Replace(_slot, () => throw new InvalidOperationException("boom"));

            Assert.DoesNotThrow(() => SessionResourceRegistry.Replace(_slot, () => second++));
            SessionResourceRegistry.Replace(_slot, () => { });

            Assert.That(second, Is.EqualTo(1));
        }

        [Test]
        public void Release_RunsThePreviousReleaseOnceAndEmptiesTheSlot()
        {
            var released = 0;
            SessionResourceRegistry.Replace(_slot, () => released++);

            SessionResourceRegistry.Release(_slot);
            SessionResourceRegistry.Release(_slot);
            SessionResourceRegistry.Replace(_slot, () => { });

            Assert.That(released, Is.EqualTo(1));
        }

        [Test]
        public void Release_FailingPreviousRelease_IsReportedAndSwallowed()
        {
            string? error = null;
            SessionResourceRegistry.Replace(_slot, () => throw new InvalidOperationException("boom"));

            Assert.DoesNotThrow(() => SessionResourceRegistry.Release(_slot, message => error = message));

            Assert.That(error, Does.Contain("boom"));
        }
    }
}

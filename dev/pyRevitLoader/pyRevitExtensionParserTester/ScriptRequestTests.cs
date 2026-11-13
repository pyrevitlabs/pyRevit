using NUnit.Framework;

using PyRevitLabs.PyRevit.Runtime;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// Request bookkeeping of the external event slot: a request that was replaced or withdrawn
    /// must never signal or alter the request that follows it.
    /// </summary>
    [TestFixture]
    public class ScriptRequestTests
    {
        [Test]
        public void SubmittingASecondRequestAbandonsTheFirstWithoutTouchingTheSecond()
        {
            var slot = new ScriptRequestSlot();
            var first = slot.Submit(null, null);

            var second = slot.Submit(null, null);

            Assert.That(first.Completed.IsSet, Is.True);
            Assert.That(first.Started.IsSet, Is.True);
            Assert.That(first.Result, Is.EqualTo(ScriptExecutorResultCodes.FailedDelayedExecutionRequest));
            Assert.That(second.Started.IsSet, Is.False);
            Assert.That(second.Completed.IsSet, Is.False);
        }

        [Test]
        public void WithdrawingTheCurrentRequestSucceedsOnceAndLeavesItUnsignalled()
        {
            var slot = new ScriptRequestSlot();
            var request = slot.Submit(null, null);

            Assert.That(slot.TryWithdraw(request), Is.True);
            Assert.That(slot.TryWithdraw(request), Is.False);
            Assert.That(request.Completed.IsSet, Is.False);
        }

        [Test]
        public void ARequestReplacedByANewerOneCannotBeWithdrawnNorWithdrawTheNewerOne()
        {
            var slot = new ScriptRequestSlot();
            var stale = slot.Submit(null, null);
            var current = slot.Submit(null, null);

            Assert.That(slot.TryWithdraw(stale), Is.False);
            Assert.That(slot.TryWithdraw(current), Is.True);
        }

        [Test]
        public void AnUnstartedRequestReportsTheFailedRequestCode()
        {
            var request = new ScriptRequestSlot().Submit(null, null);

            Assert.That(request.Result, Is.EqualTo(ScriptExecutorResultCodes.FailedDelayedExecutionRequest));
        }
    }
}

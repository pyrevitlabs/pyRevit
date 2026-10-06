using System;
using System.Threading;
using System.Threading.Tasks;

using System.Windows.Threading;

using NUnit.Framework;
using PyRevitLabs.PyRevit.Runtime;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// The output threading contract from pyRevit #3473: a script output window is WPF, so it may
    /// only be constructed on and driven from the host's UI thread. Routes serves requests on
    /// .NET worker threads, and those threads write to the same output stream as a command does -
    /// so the gate decides which threads may touch the window, and the ones that may not must be
    /// able to hand their work over without blocking.
    /// </summary>
    [TestFixture]
    [Apartment(ApartmentState.STA)]
    public class ScriptOutputUiGateTests
    {
        private ScriptOutputUiGate _gate;

        [SetUp]
        public void SetUp()
        {
            _gate = new ScriptOutputUiGate();
        }

        [Test]
        public void AnUncapturedGateAlreadyRefusesWorkerThreads()
        {
            Assert.That(_gate.HasHostUiThread, Is.False);
            Assert.That(_gate.IsHostUiThread, Is.False);

            bool allowedOnWorker = true;
            Task.Run(() => allowedOnWorker = _gate.MayCreateOutputUi).Wait();

            Assert.That(allowedOnWorker, Is.False,
                "before any capture the gate must still refuse an MTA worker, which is where every "
                    + "Routes request thread and every IronPython thread runs");
        }

        [Test]
        public void AnUncapturedGateRefusesToRecordAWorkerThreadAsTheHostUiThread()
        {
            Task.Run(() => _gate.CaptureHostUiThread()).Wait();

            Assert.That(_gate.HasHostUiThread, Is.False,
                "a worker must not be able to promote itself by capturing the gate");
        }

        [Test]
        public void TheCapturingThreadIsTheOneAllowedToTouchOutputUi()
        {
            _gate.CaptureHostUiThread();

            Assert.That(_gate.HasHostUiThread, Is.True);
            Assert.That(_gate.IsHostUiThread, Is.True);
            Assert.That(_gate.MayCreateOutputUi, Is.True);
        }

        [Test]
        public void AWorkerThreadMayNotTouchOutputUiOnceTheHostThreadIsKnown()
        {
            _gate.CaptureHostUiThread();

            bool allowedOnWorker = true;
            bool isHostOnWorker = true;
            Task.Run(() =>
            {
                allowedOnWorker = _gate.MayCreateOutputUi;
                isHostOnWorker = _gate.IsHostUiThread;
            }).Wait();

            Assert.That(allowedOnWorker, Is.False);
            Assert.That(isHostOnWorker, Is.False);
        }

        [Test]
        public void TheFirstCaptureWins()
        {
            _gate.CaptureHostUiThread();
            var hostThreadId = Thread.CurrentThread.ManagedThreadId;

            var otherStaThreadId = 0;
            var allowedOnOtherStaThread = true;
            var otherStaThread = new Thread(() =>
            {
                _gate.CaptureHostUiThread();
                allowedOnOtherStaThread = _gate.MayCreateOutputUi;
                otherStaThreadId = Thread.CurrentThread.ManagedThreadId;
            });
            otherStaThread.SetApartmentState(ApartmentState.STA);
            otherStaThread.Start();
            Assert.That(otherStaThread.Join(TimeSpan.FromSeconds(10)), Is.True);

            Assert.That(otherStaThreadId, Is.Not.EqualTo(hostThreadId));
            Assert.That(allowedOnOtherStaThread, Is.False,
                "a second STA thread is not the host UI thread, and must not be able to take over "
                    + "as the one allowed to create output windows");
            Assert.That(_gate.IsHostUiThread, Is.True);
        }

        [Test]
        public void HandOffRunsOnTheHostUiThread()
        {
            _gate.CaptureHostUiThread();

            var frame = new DispatcherFrame();
            var ranOnThreadId = 0;

            var producer = Task.Run(() => _gate.TryBeginInvoke(() =>
            {
                ranOnThreadId = Thread.CurrentThread.ManagedThreadId;
                frame.Continue = false;
            }));

            Dispatcher.PushFrame(frame);
            Assert.That(producer.Wait(TimeSpan.FromSeconds(10)), Is.True);
            Assert.That(producer.Result, Is.True);
            Assert.That(ranOnThreadId, Is.EqualTo(Thread.CurrentThread.ManagedThreadId));
        }

        [Test]
        public void HandOffOnTheHostThreadRunsInline()
        {
            _gate.CaptureHostUiThread();

            var ran = false;
            var queued = _gate.TryBeginInvoke(() => ran = true);

            Assert.That(queued, Is.True);
            Assert.That(ran, Is.True,
                "the host UI thread must not queue and return: a command's print has to render "
                    + "before the command continues");
        }

        [Test]
        public void HandOffNeverStallsTheProducerWhileTheHostUiThreadIsBusy()
        {
            _gate.CaptureHostUiThread();

            var returned = false;
            var producer = Task.Run(() =>
            {
                _gate.TryBeginInvoke(() => { });
                returned = true;
            });

            Assert.That(
                producer.Wait(TimeSpan.FromSeconds(10)),
                Is.True,
                "the producer blocked on the host UI thread, which is what made a pending Routes "
                    + "request look like a hang while a modal dialog was open");
            Assert.That(returned, Is.True);
        }

        [Test]
        public void HandOffContainsAnExceptionRaisedByTheWork()
        {
            _gate.CaptureHostUiThread();

            var frame = new DispatcherFrame();
            var producer = Task.Run(() => _gate.TryBeginInvoke(() =>
            {
                try
                {
                    throw new InvalidOperationException("rendering failed");
                }
                finally
                {
                    frame.Continue = false;
                }
            }));

            Dispatcher.PushFrame(frame);
            Assert.That(producer.Wait(TimeSpan.FromSeconds(10)), Is.True);
            Assert.That(
                producer.Result,
                Is.True,
                "an exception escaping a dispatcher callback terminates Revit, so the hand-off has "
                    + "to swallow it");
        }

        [Test]
        public void HandOffReportsFailureWithNoHostUiThread()
        {
            var ran = false;

            var queued = _gate.TryBeginInvoke(() => ran = true);

            Assert.That(queued, Is.False,
                "the caller has to be able to tell that it must fall back to a non-UI sink");
            Assert.That(ran, Is.False);
        }

        [Test]
        public void HandOffIgnoresNoWork()
        {
            _gate.CaptureHostUiThread();

            Assert.That(_gate.TryBeginInvoke(null), Is.False);
        }
    }
}

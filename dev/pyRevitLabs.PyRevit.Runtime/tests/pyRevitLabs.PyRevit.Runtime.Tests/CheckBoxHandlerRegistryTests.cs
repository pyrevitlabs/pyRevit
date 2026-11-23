using System;
using System.Collections.Generic;

using NUnit.Framework;

using PyRevitLoader;

using INotifyPropertyChanged = System.ComponentModel.INotifyPropertyChanged;
using PropertyChangedEventArgs = System.ComponentModel.PropertyChangedEventArgs;
using PropertyChangedEventHandler = System.ComponentModel.PropertyChangedEventHandler;

namespace pyRevitExtensionParserTester {
    /// <summary>
    /// A later bundle on the same checkbox control drops the change handler an earlier bundle wired
    /// before its own setup runs, other controls keep theirs, and a session release detaches every
    /// handler and refuses new ones.
    /// </summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class CheckBoxHandlerRegistryTests {
        private CheckBoxHandlerRegistry _registry = null!;
        private List<string> _calls = null!;

        [SetUp]
        public void SetUp() {
            _registry = new CheckBoxHandlerRegistry();
            _calls = new List<string>();
        }

        [TearDown]
        public void TearDown() {
            _registry.Release(_ => { });
        }

        [Test]
        public void Wire_ControlChanges_CallTheHandler() {
            var checkBox = new FakeCheckBox();

            var wired = _registry.Wire(checkBox, Handler("first"));
            checkBox.RaiseIsCheckedChanged();
            checkBox.RaiseIsCheckedChanged();

            Assert.That(wired, Is.True);
            Assert.That(_calls, Is.EqualTo(new[] { "first", "first" }));
        }

        [Test]
        public void DetachEarlier_ThenALaterBundleOnTheSameControl_OnlyTheLaterHandlerRuns() {
            var checkBox = new FakeCheckBox();
            _registry.Wire(checkBox, Handler("earlier"));

            var detached = _registry.DetachEarlier(checkBox);
            checkBox.RaiseIsCheckedChanged();
            _registry.Wire(checkBox, Handler("later"));
            checkBox.RaiseIsCheckedChanged();

            Assert.That(detached, Is.True);
            Assert.That(_calls, Is.EqualTo(new[] { "later" }));
            Assert.That(checkBox.SubscriberCount, Is.EqualTo(1));
        }

        [Test]
        public void DetachEarlier_ControlWithoutAHandler_DetachesNothing() {
            Assert.That(_registry.DetachEarlier(new FakeCheckBox()), Is.False);
        }

        [Test]
        public void DetachEarlier_KeepsTheHandlersOfOtherControls() {
            var other = new FakeCheckBox();
            var shared = new FakeCheckBox();
            _registry.Wire(other, Handler("other"));
            _registry.Wire(shared, Handler("shared"));

            _registry.DetachEarlier(shared);
            shared.RaiseIsCheckedChanged();
            other.RaiseIsCheckedChanged();

            Assert.That(_calls, Is.EqualTo(new[] { "other" }));
        }

        [Test]
        public void Release_DetachesEveryHandler() {
            var first = new FakeCheckBox();
            var second = new FakeCheckBox();
            _registry.Wire(first, Handler("first"));
            _registry.Wire(second, Handler("second"));

            _registry.Release(_ => { });
            first.RaiseIsCheckedChanged();
            second.RaiseIsCheckedChanged();

            Assert.That(_registry.IsReleased, Is.True);
            Assert.That(_calls, Is.Empty);
            Assert.That(first.SubscriberCount + second.SubscriberCount, Is.EqualTo(0));
        }

        [Test]
        public void Wire_AfterRelease_SubscribesNothing() {
            var checkBox = new FakeCheckBox();
            _registry.Release(_ => { });

            var wired = _registry.Wire(checkBox, Handler("late"));
            checkBox.RaiseIsCheckedChanged();

            Assert.That(wired, Is.False);
            Assert.That(_calls, Is.Empty);
            Assert.That(checkBox.SubscriberCount, Is.EqualTo(0));
        }

        [Test]
        public void Release_HandlerThatFailsToDetach_IsReportedAndTheOthersStillDetach() {
            var other = new FakeCheckBox();
            _registry.Wire(new CheckBoxThatFailsToDetach(), Handler("failing"));
            _registry.Wire(other, Handler("other"));
            var errors = new List<string>();

            _registry.Release(errors.Add);
            other.RaiseIsCheckedChanged();

            Assert.That(errors, Has.Count.EqualTo(1));
            Assert.That(errors[0], Does.Contain("detach failed"));
            Assert.That(_calls, Is.Empty);
        }

        [Test]
        public void Release_ErrorReportThatThrows_StillDetachesTheOtherHandlers() {
            var other = new FakeCheckBox();
            _registry.Wire(new CheckBoxThatFailsToDetach(), Handler("failing"));
            _registry.Wire(other, Handler("other"));

            Assert.DoesNotThrow(() => _registry.Release(_ => throw new InvalidOperationException("report failed")));
            other.RaiseIsCheckedChanged();

            Assert.That(_calls, Is.Empty);
            Assert.That(other.SubscriberCount, Is.EqualTo(0));
        }

        private PropertyChangedEventHandler Handler(string name) {
            return (sender, args) => _calls.Add(name);
        }

        private sealed class FakeCheckBox : INotifyPropertyChanged {
            public event PropertyChangedEventHandler? PropertyChanged;

            public int SubscriberCount => PropertyChanged?.GetInvocationList().Length ?? 0;

            public void RaiseIsCheckedChanged() {
                PropertyChanged?.Invoke(this, new PropertyChangedEventArgs("IsChecked"));
            }
        }

        private sealed class CheckBoxThatFailsToDetach : INotifyPropertyChanged {
            public event PropertyChangedEventHandler? PropertyChanged {
                add { }
                remove { throw new InvalidOperationException("detach failed"); }
            }
        }
    }
}

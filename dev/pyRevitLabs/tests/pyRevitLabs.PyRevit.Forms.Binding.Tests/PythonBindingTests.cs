using System.Collections;
using System.ComponentModel;
using PyRevitLabs.PyRevit.Forms.Binding;
using Python.Runtime;
using Xunit;

namespace PyRevitLabs.PyRevit.Forms.Binding.Tests;

/// <summary>Plain Python data behaves in real WPF under pythonnet as it does under IronPython.</summary>
[Collection(PythonWpfCollection.Name)]
public class PythonBindingTests(PythonWpfHost host) {
    private const string Common = @"
import clr
import System
from collections import namedtuple
from System.Windows import Controls, Data, Markup, Window, WindowStartupLocation
from System.ComponentModel import ListSortDirection, SortDescription


class Item(object):
    __hash__ = None

    def __init__(self, name, count, active=True):
        self.name = name
        self.count = count
        self.active = active

    def __eq__(self, other):
        raise AssertionError('WPF must not use Python equality')


def read(model, path):
    text = Controls.TextBlock()
    text.DataContext = model
    text.SetBinding(Controls.TextBlock.TextProperty, Data.Binding(path)).UpdateTarget()
    return text.Text


def shown(content):
    window = Window()
    window.ShowActivated = False
    window.WindowStartupLocation = WindowStartupLocation.Manual
    window.Left = -20000
    window.Content = content
    window.Show()
    window.UpdateLayout()
    return window
";

    private void Python(string code) {
        host.Exec(Common + code);
    }

    [Fact]
    public void CodecsRegisteredLateReplaceCachedConversions() {
        Assert.True(host.EarlyListFailed);
        Assert.IsType<PythonObjectProxy>(host.EarlyHolderItem);
    }

    [Fact]
    public void IntsPassedAsObjectsBecomeClrIntegers() {
        host.Run(() => {
            ArrayList holder;
            using (Py.GIL()) {
                using var scope = Py.CreateScope();
                scope.Exec(Common + "holder = System.Collections.ArrayList()\nfor value in (5, 2 ** 40, 2 ** 80, True):\n    holder.Add(value)\nassert holder[0] == 5 and holder[2] == 2 ** 80\n");
                holder = (ArrayList)scope.Get("holder").AsManagedObject(typeof(ArrayList));
            }
            Assert.IsType<int>(holder[0]);
            Assert.IsType<long>(holder[1]);
            Assert.IsNotType<long>(holder[2]);
            Assert.IsType<bool>(holder[3]);
        });
        Python(@"
class Model(object):
    def __init__(self):
        self.level = 2
        self.levels = [Item('L1', 1), Item('L2', 2)]

combo = Controls.ComboBox()
combo.DisplayMemberPath = 'name'
combo.SelectedValuePath = 'count'
combo.SetBinding(Controls.ItemsControl.ItemsSourceProperty, Data.Binding('levels'))
binding = Data.Binding('level')
binding.Mode = Data.BindingMode.TwoWay
combo.SetBinding(Controls.Primitives.Selector.SelectedValueProperty, binding)
model = Model()
combo.DataContext = model
window = shown(combo)
try:
    assert combo.SelectedIndex == 1
    combo.SelectedIndex = 0
    assert model.level == 1 and type(model.level) is int
finally:
    window.Close()
");
    }

    [Fact]
    public void ListSourceIsLiveAndReadsBackAsTheSamePythonList() {
        Python(@"
items = [Item('a', 1), Item('b', 2)]
box = Controls.ListBox()
box.ItemsSource = items
assert box.ItemsSource is items
assert box.Items.Count == 2
items.append(Item('c', 3))
box.Items.Refresh()
assert box.Items.Count == 3
assert box.Items[2] is items[2]
del items[0]
box.Items.Refresh()
assert box.Items.Count == 2 and box.Items[0] is items[0]
assert box.ItemsSource.index(items[0]) == 0
");
    }

    [Fact]
    public void ItemsGoBackToPythonAsTheOriginalObjects() {
        Python(@"
items = [Item('a', 1), Item('b', 2), Item('c', 3)]
box = Controls.ListBox()
added = []
box.SelectionChanged += lambda sender, args: added.extend(args.AddedItems)
box.ItemsSource = items
window = shown(box)
try:
    box.SelectedIndex = 1
    assert box.SelectedItem is items[1]
    assert added[0] is items[1]
    assert box.Items[2] is items[2]
    assert all(a is b for a, b in zip(box.Items, items))
    container = box.ItemContainerGenerator.ContainerFromItem(items[2])
    assert container is not None
    assert container.DataContext is items[2]
    box.SelectedItem = items[0]
    assert box.SelectedIndex == 0
finally:
    window.Close()

tagged = Controls.TextBlock()
tagged.Tag = items[0]
assert tagged.Tag is items[0]
tagged.DataContext = items[1]
assert tagged.DataContext is items[1]
");
    }

    [Fact]
    public void AttributesConvertToClrValuesForBindings() {
        Python(@"
class Child(object):
    def __init__(self):
        self.label = 'child'

class Model(object):
    def __init__(self):
        self.flag = True
        self.count = 7
        self.big = 2 ** 40
        self.ratio = 0.5
        self.text = 'hello'
        self.nothing = None
        self.child = Child()
        self.values = ['x', 'y']

    @property
    def computed(self):
        return self.count * 2

    def __getattr__(self, name):
        if name == 'dynamic':
            return 'from getattr'
        raise AttributeError(name)

model = Model()
assert read(model, 'text') == 'hello'
assert read(model, 'count') == '7'
assert read(model, 'computed') == '14'
assert read(model, 'child.label') == 'child'
assert read(model, 'values[1]') == 'y'
assert read(model, 'values.Count') == '2'
assert read(model, 'dynamic') == 'from getattr'
model.text = 'changed'
assert read(model, 'text') == 'changed'

Point = namedtuple('Point', 'x y')
assert read(Point(3, 4), 'y') == '4'
");
        host.Run(() => {
            object proxy;
            using (Py.GIL()) {
                using var scope = Py.CreateScope();
                scope.Exec(Common + "class Model(object):\n    def __init__(self):\n        self.flag = True\n        self.count = 7\n        self.big = 2 ** 40\n        self.ratio = 0.5\n        self.text = 'hello'\n        self.nothing = None\n        self.values = [1]\nholder = System.Collections.ArrayList()\nholder.Add(Model())\n");
                proxy = ((ArrayList)scope.Get("holder").AsManagedObject(typeof(ArrayList)))[0]!;
            }
            var properties = TypeDescriptor.GetProperties(proxy);
            Assert.Equal(true, properties["flag"]!.GetValue(proxy));
            Assert.Equal(7, properties["count"]!.GetValue(proxy));
            Assert.Equal(1L << 40, properties["big"]!.GetValue(proxy));
            Assert.Equal(0.5, properties["ratio"]!.GetValue(proxy));
            Assert.Equal("hello", properties["text"]!.GetValue(proxy));
            Assert.Null(properties["nothing"]!.GetValue(proxy));
            Assert.IsType<PythonListProxy>(properties["values"]!.GetValue(proxy));
            Assert.Null(properties["missing"]);
        });
    }

    [Fact]
    public void TwoWayBindingsWriteBackToPython() {
        Python(@"
class Model(object):
    def __init__(self):
        self.name = 'before'
        self.flag = False
        self._size = 1

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        self._size = int(value)

model = Model()
editor = Controls.TextBox()
editor.DataContext = model
expression = editor.SetBinding(Controls.TextBox.TextProperty, Data.Binding('name'))
expression.UpdateTarget()
assert editor.Text == 'before'
editor.Text = 'after'
expression.UpdateSource()
assert model.name == 'after'

check = Controls.CheckBox()
check.DataContext = model
binding = Data.Binding('flag')
binding.Mode = Data.BindingMode.TwoWay
check.SetBinding(Controls.CheckBox.IsCheckedProperty, binding)
check.IsChecked = True
assert model.flag is True

sizer = Controls.TextBox()
sizer.DataContext = model
sized = sizer.SetBinding(Controls.TextBox.TextProperty, Data.Binding('size'))
sizer.Text = '5'
sized.UpdateSource()
assert model.size == 5

mirror = Controls.TextBlock()
mirror.DataContext = model
mirror.SetBinding(Controls.TextBlock.TextProperty, Data.Binding('name'))
editor.Text = 'synced'
expression.UpdateSource()
assert mirror.Text == 'synced'
");
    }

    [Fact]
    public void DataTriggersCompareConvertedValues() {
        Python(@"
markup = '''
<Border xmlns='http://schemas.microsoft.com/winfx/2006/xaml/presentation'>
  <Border.Style>
    <Style TargetType='Border'>
      <Setter Property='Tag' Value='none'/>
      <Style.Triggers>
        <DataTrigger Binding='{Binding active}' Value='True'><Setter Property='Tag' Value='active'/></DataTrigger>
        <DataTrigger Binding='{Binding name}' Value='special'><Setter Property='Tag' Value='special'/></DataTrigger>
        <DataTrigger Binding='{Binding count}' Value='3'><Setter Property='Tag' Value='three'/></DataTrigger>
      </Style.Triggers>
    </Style>
  </Border.Style>
</Border>'''
cases = [(Item('a', 1, True), 'active'), (Item('special', 1, False), 'special'),
         (Item('b', 3, False), 'three'), (Item('c', 1, False), 'none')]
for item, expected in cases:
    border = Markup.XamlReader.Parse(markup)
    border.DataContext = item
    window = shown(border)
    try:
        assert str(border.Tag) == expected, (item.name, border.Tag)
    finally:
        window.Close()
");
    }

    [Fact]
    public void SortingFilteringAndPathsUseProxiedValues() {
        Python(@"
items = [Item('c', 3), Item('a', 1), Item('b', 2)]
box = Controls.ListBox()
box.ItemsSource = items
box.DisplayMemberPath = 'name'
box.SelectedValuePath = 'count'
box.Items.SortDescriptions.Add(SortDescription('count', ListSortDirection.Ascending))
assert [item.name for item in box.Items] == ['a', 'b', 'c']
assert box.Items[0] is items[1]

seen = []
def keep(item):
    seen.append(item)
    return item.count > 1
box.Items.Filter = System.Predicate[System.Object](keep)
assert box.Items.Count == 2
assert all(any(item is original for original in items) for item in seen)

window = shown(box)
try:
    box.SelectedIndex = 0
    assert box.SelectedValue == 2
    assert box.SelectedItem is items[2]
finally:
    window.Close()

grid = Controls.DataGrid()
grid.AutoGenerateColumns = True
grid.ItemsSource = [Item('a', 1)]
window = shown(grid)
try:
    headers = [str(column.Header) for column in grid.Columns]
    assert headers == ['name', 'count', 'active'], headers
finally:
    window.Close()
");
    }

    [Fact]
    public void DictItemsAreSelectableAndBindTheirKeys() {
        Python(@"
items = [{'name': 'first'}, {'name': 'second'}]
box = Controls.ListBox()
box.ItemsSource = items
box.DisplayMemberPath = 'name'
window = shown(box)
try:
    box.SelectedIndex = 1
    assert box.SelectedItem is items[1]
    box.SelectedIndex = 0
    assert box.SelectedItem is items[0]
finally:
    window.Close()

wrapper = Item('wrapper', 0)
wrapper.records = items
editor = Controls.TextBox()
editor.DataContext = wrapper
editor.SetBinding(Controls.TextBox.TextProperty, Data.Binding('records[1].name'))
expression = editor.GetBindingExpression(Controls.TextBox.TextProperty)
expression.UpdateTarget()
assert editor.Text == 'second'
editor.Text = 'edited'
expression.UpdateSource()
assert items[1]['name'] == 'edited'
");
    }

    [Fact]
    public void NonSequenceIterablesAreCopiedAndTuplesAreReadOnly() {
        Python(@"
box = Controls.ListBox()
values = {'one', 'two'}
box.ItemsSource = values
assert box.Items.Count == 2
assert box.ItemsSource is values

box.ItemsSource = (x for x in range(3))
assert box.Items.Count == 3

box.ItemsSource = ('a', 'b')
assert box.Items.Count == 2
assert box.Items[1] == 'b'
");
    }

    [Fact]
    public void ProxiesTakeTheGilForCallersThatReleasedIt() {
        IList? list = null;
        object? item = null;
        host.Run(() => {
            using (Py.GIL()) {
                using var scope = Py.CreateScope();
                scope.Exec(Common + "values = [Item('a', 1), Item('b', 2)]\nholder = System.Collections.ArrayList()\nholder.Add(Controls.ListBox())\nholder[0].ItemsSource = values\n");
                var box = (System.Windows.Controls.ListBox)((ArrayList)scope.Get("holder").AsManagedObject(typeof(ArrayList)))[0]!;
                list = (IList)box.ItemsSource;
            }
            Assert.Equal(2, list.Count);
            item = list[1];
            Assert.Equal("b", TypeDescriptor.GetProperties(item!)["name"]!.GetValue(item));
        });

        var worker = Task.Run(() => {
            Assert.Equal(2, list!.Count);
            Assert.Equal(1, list.IndexOf(item));
            Assert.Equal(2, TypeDescriptor.GetProperties(item!)["count"]!.GetValue(item));
            Assert.False(string.IsNullOrEmpty(item!.ToString()));
        });
        Assert.True(worker.Wait(TimeSpan.FromSeconds(20)), "Proxy access without the GIL deadlocked.");
    }

    [Fact]
    public void AdapterHooksMapModelsBothWays() {
        Python(@"
from System.Dynamic import ExpandoObject
from PyRevitLabs.PyRevit.Forms.Binding import PythonBinding

class Marked(object):
    pass

marked = Marked()
native = ExpandoObject()
models = {}

def adapt(value):
    if isinstance(value, Marked):
        models[native] = value
        return native
    return None

PythonBinding.Register(adapt, models.get)
try:
    text = Controls.TextBlock()
    text.DataContext = marked
    assert text.DataContext is marked
    plain = Item('p', 1)
    text.DataContext = plain
    assert text.DataContext is plain
finally:
    PythonBinding.Register(None, None)
");
    }

    [Fact]
    public void ControllersConvertToTheirNativeRootForTypedTargets() {
        Python(@"
from System.Windows import DependencyObject, Interop
from PyRevitLabs.PyRevit.Forms.Binding import PythonBinding


class Controller(object):
    root_type = Window

    def __init__(self):
        self.root = shown(Controls.Grid())


class Other(object):
    pass


PythonBinding.RegisterRoots(
    lambda cls: clr.GetClrType(cls.root_type) if hasattr(cls, 'root_type') else None,
    lambda value: getattr(value, 'root', None),
)
try:
    parent = Controller()
    child = Window()
    child.Owner = parent
    assert System.Object.ReferenceEquals(child.Owner, parent.root)
    helper = Interop.WindowInteropHelper(parent)
    assert helper.Handle == Interop.WindowInteropHelper(parent.root).Handle
    Controls.Grid.SetRow(parent, 2)
    assert Controls.Grid.GetRow(parent.root) == 2
    holder = Controls.Border()
    holder.Tag = parent
    assert holder.Tag is parent
    try:
        child.Owner = Other()
        raise AssertionError('a plain object became a Window')
    except TypeError:
        pass
    try:
        Controls.TextBlock().Text = parent
        raise AssertionError('a controller became a string')
    except TypeError:
        pass
finally:
    PythonBinding.RegisterRoots(None, None)
    child.Close()
    parent.root.Close()
");
    }

    [Fact]
    public void HookedElementsReachTheirCallbackForEveryTemplateInstance() {
        Python(@"
from PyRevitLabs.PyRevit.Forms.Binding import PythonEvents

seen = []
PythonEvents.Attach('probe-key', lambda element: seen.append(element))
try:
    template = Markup.XamlReader.Parse(
        '<DataTemplate xmlns=""http://schemas.microsoft.com/winfx/2006/xaml/presentation"" '
        'xmlns:e=""clr-namespace:PyRevitLabs.PyRevit.Forms.Binding;assembly=pyRevitLabs.PyRevit.Forms.Binding"">'
        '<TextBlock><TextBlock.ContextMenu><ContextMenu>'
        '<MenuItem Header=""Do"" e:PythonEvents.Hook=""probe-key""/>'
        '</ContextMenu></TextBlock.ContextMenu></TextBlock></DataTemplate>'
    )
    first = template.LoadContent()
    second = template.LoadContent()
    assert len(seen) == 2
    assert System.Object.ReferenceEquals(seen[0], first.ContextMenu.Items[0])
    assert System.Object.ReferenceEquals(seen[1], second.ContextMenu.Items[0])
    PythonEvents.Detach('probe-key')
    template.LoadContent()
    assert len(seen) == 2
finally:
    PythonEvents.Detach('probe-key')
");
    }
}

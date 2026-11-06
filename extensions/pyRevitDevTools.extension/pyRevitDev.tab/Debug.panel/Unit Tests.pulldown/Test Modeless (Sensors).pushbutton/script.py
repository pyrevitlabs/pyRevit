""" """

# pylint: skip-file
from pyrevit import HOST_APP, framework, EXEC_PARAMS
from pyrevit import forms
from pyrevit import revit, DB, UI
from pyrevit.runtime import types as runtime_types
from pyrevit.framework import Input
from pyrevit import script


logger = script.get_logger()


class SensorGroup(forms.Reactive):
    def __init__(self, header, sensors):
        self.header = header.upper()
        self._sensors = sensors

    @forms.reactive
    def sensors(self):
        return self._sensors

    @sensors.setter
    def sensors(self, value):
        self._sensors = value


class Sensor(forms.Reactive):
    def __init__(self, header, value="", has_progress=False, category_id=None):
        self._header = header
        self._value = value
        self._has_progress = has_progress
        self._progress = 0.0
        self._progress_max = 1.0
        self.category_id = category_id

    @forms.reactive
    def header(self):
        return self._header

    @forms.reactive
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    @forms.reactive
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value):
        self._progress = value

    @forms.reactive
    def progress_max(self):
        return self._progress_max

    @progress_max.setter
    def progress_max(self, value):
        self._progress_max = value

    @forms.reactive
    def has_progress(self):
        return self._has_progress

    @has_progress.setter
    def has_progress(self, value):
        self._has_progress = value


def _count_all_elements(doc):
    return (
        DB.FilteredElementCollector(doc)
        .WherePasses(
            DB.LogicalOrFilter(
                DB.ElementIsElementTypeFilter(False),
                DB.ElementIsElementTypeFilter(True),
            )
        )
        .GetElementCount()
    )


def _count_category_instances(doc, category_id):
    return (
        DB.FilteredElementCollector(doc)
        .OfCategoryId(category_id)
        .WhereElementIsNotElementType()
        .GetElementCount()
    )


def _refresh_scheduled_update():
    ui._run_scheduled_update()


class NonModalWindow(forms.WPFWindow):
    def __init__(self):
        pass

    def setup(self):
        # self.set_image_source(self.icon, 'sensors.png')
        self._update_scheduled = False
        self._closed = False
        self.doc_title_snsr = Sensor("Title")
        self.doc_elmnts_snsr = Sensor("Elements", has_progress=True)
        self.doc_snsrs = SensorGroup(
            "Document", [self.doc_title_snsr, self.doc_elmnts_snsr]
        )
        self.cat_snsrs = SensorGroup("Categories", self.make_category_sensors())
        self.sensor_groups = [self.doc_snsrs, self.cat_snsrs]
        self.sensorsPanel.ItemsSource = self.sensor_groups
        self.update_ui()

    @revit.events.handle("doc-changed", "doc-closed", "doc-opened", "view-activated")
    def uiupdator_eventhandler(sender, args):
        # the decorator captures the function from the class and not from the
        # instance. so the capture function is not bound thus no 'self'
        # ui however is inside the context and still accessible
        ui.schedule_update()

    def schedule_update(self):
        """Queue one coalesced ``update_ui`` through an ExternalEvent.

        Note:
            Event handlers must not refresh synchronously: a refresh counts
            every category and would block Revit on each model change. Events
            raised before the queued refresh runs share that one refresh. A
            refresh that could not be queued leaves the next event free to
            queue again.
        """
        if self._update_scheduled or self._closed:
            return
        self._update_scheduled = True
        queued = False
        try:
            queued = revit.events.execute_in_revit_context(_refresh_scheduled_update)
        finally:
            if not queued:
                self._update_scheduled = False

    def _run_scheduled_update(self):
        self._update_scheduled = False
        if not self._closed:
            self.update_ui()

    def update_ui(self):
        if revit.doc:
            self.doc_title_snsr.value = revit.doc.Title
            count = _count_all_elements(revit.doc)
            self.doc_elmnts_snsr.value = str(count)
            self.doc_elmnts_snsr.progress = float(count)

            self.update_category_sensors(self.cat_snsrs.sensors, count)
        else:
            self.doc_title_snsr.value = "N/A"
            self.doc_elmnts_snsr.value = 0

    def make_category_sensors(self):
        sensors = []
        for cat in revit.query.get_doc_categories(doc=revit.doc, include_subcats=False):
            sensors.append(Sensor(cat.Name, has_progress=True, category_id=cat.Id))
        return sensors

    def sort_category_sensors_list(self):
        self.cat_snsrs.sensors = sorted(
            self.cat_snsrs.sensors, key=lambda x: x.progress, reverse=True
        )

    def update_category_sensors(self, sensors, max_count):
        """Count instances per category sensor and re-sort by count.

        Args:
            sensors: Category sensors to refresh; sensors without a
                ``category_id`` are skipped.
            max_count: Document-wide element count used as every sensor's
                ``progress_max``.

        Note:
            Uses ``FilteredElementCollector``, so it must run in Revit API
            context.
        """
        for sensor in sensors:
            if sensor.category_id is not None:
                count = _count_category_instances(revit.doc, sensor.category_id)
                sensor.value = count
                sensor.progress = float(count)
                sensor.progress_max = float(max_count)
        self.sort_category_sensors_list()

    def window_moving(self, sender, args):
        if args.ChangedButton == Input.MouseButton.Left:
            self.DragMove()

    def window_closing(self, sender, args):  # pylint: disable=unused-argument
        self._closed = True
        revit.events.stop_events()


ui = script.load_ui(NonModalWindow(), ui_file="sensors.xaml")

ui.show(modal=__shiftclick__)

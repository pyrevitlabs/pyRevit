"""Manage tags in project or selected elements."""
#pylint: disable=C0111,E0401,C0103,W0613,W0703
from pyrevit import revit
from pyrevit.revit import query
from pyrevit import forms
from pyrevit import script

import tagscfg
import tagsmgr


__title__ = 'Manage\nTags'
__author__ = '{{author}}'
__helpurl__ = '{{docpath}}FYNDSAypWlg'


logger = script.get_logger()


class ManageTagsWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        selection = revit.get_selection()
        sel_cnt = len(selection)
        if sel_cnt:
            forms.alert('You are managing tags on {} selected elements only.'
                        .format(sel_cnt))

        forms.WPFWindow.__init__(self, xaml_file_name)
        if sel_cnt > 0:
            self.Title += ' (for {} Selected Elements)'.format(sel_cnt) #pylint: disable=E1101
            # self.hide_element(self.select_elements_b)
            self._target_elements = selection.elements
            self._context = \
                tagsmgr.get_available_tags(self._target_elements)
        else:
            self._target_elements = None
            self._context = tagsmgr.get_available_tags()
            elmnt_count = tagsmgr.get_last_metadata()['count']
            self.Title += ' (for {} Elements)'.format(elmnt_count) #pylint: disable=E1101

        self.tagmodif_template = \
            self.Resources["ModifierListItemControlTemplate"]
        self._list_options()
        self.hide_element(self.clrsearch_b)
        self.clear_search(None, None)
        self.search_tb.Focus()

    def _list_options(self, option_filter=None):
        if option_filter:
            option_filter = option_filter.lower()
            self.taglist_lb.ItemsSource = \
                [x for x in self._context if option_filter in x.tagid.lower()]
        else:
            self.taglist_lb.ItemsSource = [x for x in self._context]

    def _get_options(self):
        return list(self.taglist_lb.SelectedItems)

    def search_txt_changed(self, sender, args):
        """Handle text change in search box."""
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._list_options(option_filter=self.search_tb.Text)

    def clear_search(self, sender, args):
        """Clear search box."""
        self.search_tb.Text = ' '
        self.search_tb.Clear()
        self.search_tb.Focus()

    @property
    def selected_tags(self):
        return self._get_options()

    def get_single_tag(self):
        if len(self.selected_tags) == 1:
            return self.selected_tags[0]
        elif len(self.selected_tags) > 1:
            forms.alert('Please select one tag only.')

    def select_tag(self, sender, args):
        if self.selected_tags:
            self.Close()
            tagsmgr.select_tag_elements(self.selected_tags)

    def update_selection(self, sender, args):
        selc_tags_count = len(self.selected_tags)
        if selc_tags_count == 0:
            self.disable_element(self.select_elements_b)
            self.disable_element(self.rename_tag_b)
            self.disable_element(self.delete_tag_b)
            self.disable_element(self.create_3dview)
            self.disable_element(self.create_schedules_b)
            self.disable_element(self.create_filter_b)
            self.disable_element(self.apply_modif_b)
            self.disable_element(self.remove_modif_b)
        elif selc_tags_count == 1:
            self.enable_element(self.select_elements_b)
            self.enable_element(self.rename_tag_b)
            self.enable_element(self.delete_tag_b)
            self.enable_element(self.create_3dview)
            self.enable_element(self.create_schedules_b)
            self.enable_element(self.create_filter_b)
            self.enable_element(self.apply_modif_b)
            self.enable_element(self.remove_modif_b)
        elif selc_tags_count > 1:
            self.enable_element(self.select_elements_b)
            self.disable_element(self.rename_tag_b)
            self.disable_element(self.delete_tag_b)
            self.disable_element(self.create_schedules_b)
            if selc_tags_count > 3:
                self.disable_element(self.create_3dview)
                self.disable_element(self.create_filter_b)
            else:
                self.enable_element(self.create_3dview)
                self.enable_element(self.create_filter_b)

    def copy_tagid(self, sender, args):
        tags = '\r\n'.join([x.name for x in self.taglist_lb.SelectedItems])
        script.clipboard_copy(tags)

    def delete_tag(self, sender, args):
        if self.selected_tags:
            self.Close()
            try:
                with revit.Transaction('Delete Tag'):
                    tagsmgr.remove_tag(self.selected_tags[0],
                                       self._target_elements)
            except Exception as e:
                forms.alert(getattr(e, 'msg', str(e)))

    def rename_tag(self, sender, args):
        if self.selected_tags:
            self.Close()
            new_tag = forms.ask_for_string(
                default=self.selected_tags[0].name,
                prompt='Enter new tag name:',
                title='Tag Manager'
                )
            if new_tag:
                try:
                    with revit.Transaction('Rename Tag', log_errors=False):
                        tagsmgr.rename_tag(self.selected_tags[0],
                                           new_tag,
                                           self._target_elements)
                except Exception as e:
                    forms.alert(getattr(e, 'msg', str(e)))

    def add_modifier(self, sender, args):
        if self.selected_tags:
            modifs = set()
            for sel_tag in self.selected_tags:
                modifs.update(sel_tag.modifiers)
            modifiers = \
                forms.SelectFromList.show(
                    tagsmgr.TagModifiers.get_modifiers() - modifs,
                    title='Select Modifier',
                    button_name='Select Modifier',
                    width=400,
                    height=300,
                    item_template=self.tagmodif_template
                    )
            if modifiers:
                self.Close()
                try:
                    with revit.Transaction('Apply Tag Modifier',
                                           log_errors=False):
                        tagsmgr.add_modifier(self.selected_tags,
                                             modifiers,
                                             self._target_elements)
                except Exception as e:
                    forms.alert(getattr(e, 'msg', str(e)))

    def remove_modifier(self, sender, args):
        if self.selected_tags:
            modifs = set()
            for sel_tag in self.selected_tags:
                modifs.update(sel_tag.modifiers)
            modifiers = \
                forms.SelectFromList.show(
                    modifs,
                    title='Select Modifier',
                    button_name='Select Modifier',
                    width=400,
                    height=300,
                    item_template=self.tagmodif_template
                    )
            if modifiers:
                self.Close()
                try:
                    with revit.Transaction('Remove Tag Modifier',
                                           log_errors=False):
                        tagsmgr.remove_modifier(self.selected_tags,
                                                modifiers,
                                                self._target_elements)
                except Exception as e:
                    forms.alert(getattr(e, 'msg', str(e)))

    def make_filter(self, sender, args):
        if self.selected_tags:
            self.Close()
            try:
                with revit.Transaction('Create Tag Filters',
                                       log_errors=False):
                    tagsmgr.create_tag_filter(self.selected_tags)
                    tagsmgr.create_tag_filter(self.selected_tags, exclude=True)
            except Exception as e:
                forms.alert(getattr(e, 'msg', str(e)))

    def make_modifier_filters(self, sender, args):
        self.Close()
        try:
            with revit.Transaction('Create Modifier Filters',
                                   log_errors=False):
                tagsmgr.create_modifier_filters()
                tagsmgr.create_modifier_filters(exclude=True)
        except Exception as e:
            forms.alert(getattr(e, 'msg', str(e)))

    def make_schedule(self, sender, args):
        tag = self.get_single_tag()
        if tag:
            selements = tagsmgr.get_all_tag_elements(tag)
            tag_cat = \
                forms.SelectFromList.show(
                    query.get_element_categories(selements),
                    name_attr='Name',
                    title='Select Schedule Category',
                    button_name='Select Category',
                    width=400, height=300
                    )
            if tag_cat:
                cat_schedules = query.get_category_schedules(tag_cat)
                if not cat_schedules:
                    forms.alert('There are no schedules for {catname} in the '
                                'model. Create a schedule for {catname} and '
                                'select the desired fields. This tool will '
                                'duplicate the schedule and filter for the '
                                'selected tag.'
                                .format(catname=tag_cat.Name))
                    return
                tag_sched = \
                    forms.SelectFromList.show(
                        query.get_category_schedules(tag_cat),
                        name_attr='ViewName',
                        title='Select Template Schedule',
                        button_name='Select Schedule',
                        width=400, height=300
                        )
                if tag_sched:
                    self.Close()
                    with revit.Transaction('Create Tag Schedule ({})'
                                           .format(tag_cat.Name)):
                        new_Sched = \
                            tagsmgr.create_tag_schedule(tag,
                                                        tag_cat,
                                                        tag_sched)
                    revit.active_view = new_Sched

    def make_tag_3dview(self, sender, args):
        if self.selected_tags:
            self.Close()
            try:
                with revit.Transaction('Create Tag 3D View',
                                       log_errors=False):
                    tag_view = \
                        tagsmgr.create_tag_3dview(self.selected_tags)

                revit.active_view = tag_view
            except Exception as e:
                forms.alert(getattr(e, 'msg', str(e)))


# make sure doc is not family
forms.check_modeldoc(doc=revit.doc, exitscript=True)

if tagscfg.verify_tags_configs():
    ManageTagsWindow('ManageTagsWindow.xaml').ShowDialog()
else:
    forms.alert('Tags tools need to be configured before using. '
                'Click on the Tags Settings button to setup.')

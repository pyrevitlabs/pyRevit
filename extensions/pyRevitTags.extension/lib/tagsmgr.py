"""Module for managing tags metadata."""
#pylint: disable=E0401,C0111,W0603,C0103
from collections import namedtuple, defaultdict

from pyrevit import framework
from pyrevit import PyRevitException
from pyrevit.coreutils import pyutils
from pyrevit.coreutils import logger
from pyrevit import revit, DB
from pyrevit.revit import query
from pyrevit.revit import create

import tagscfg


mlogger = logger.get_logger(__name__)


_METADATA_DICT = None

# elements of these categories adopt the tag of parent
# if not skipped, they'll show up as part of tag elements
SCOPE_SKIP_CATEGORIES = [
    # all center lines related to parameteric components
    DB.BuiltInCategory.OST_FabricationContainmentCenterLine,
    DB.BuiltInCategory.OST_FabricationPipeworkCenterLine,
    DB.BuiltInCategory.OST_FabricationDuctworkCenterLine,
    DB.BuiltInCategory.OST_ConduitFittingCenterLine,
    DB.BuiltInCategory.OST_CableTrayFittingCenterLine,
    DB.BuiltInCategory.OST_ConduitCenterLine,
    DB.BuiltInCategory.OST_CableTrayCenterLine,
    DB.BuiltInCategory.OST_PipeFittingCenterLine,
    DB.BuiltInCategory.OST_DuctFittingCenterLine,
    DB.BuiltInCategory.OST_FlexPipeCurvesCenterLine,
    DB.BuiltInCategory.OST_PipeCurvesCenterLine,
    DB.BuiltInCategory.OST_FlexDuctCurvesCenterLine,
    DB.BuiltInCategory.OST_DuctCurvesCenterLine,
    DB.BuiltInCategory.OST_DSR_CenterlineTickMarkStyleId,
    DB.BuiltInCategory.OST_DSR_CenterlinePatternCatId,
    DB.BuiltInCategory.OST_CenterLines,
    DB.BuiltInCategory.OST_StairsSketchLandingCenterLines
    ]


ApplyTagsConfig = namedtuple('ApplyTagsConfig', ['append', 'circuits'])
"""namedtuple for configuring the behaviour of :func:`apply_tags`

Attributes:
    append (bool): append tag to existing tags on elements
    circuits (bool): apply tag to circuits connected to selected elements
"""


class TagModifier(object):
    """Class representing a tag modifier.

    This class implements __eq__, __lt__, and __hash__ for direct comparision,
    inclusion tests, and to be included in hashtables e.g. sets

    Args:
        name (str): tag modifier name (e.g. Issued for Fabrication)
        abbrev (str): tag modifier abbreviation (e.g. IFF)

    Attributes:
        name (str): tag modifier name (e.g. Issued for Fabrication)
        abbrev (str): tag modifier abbreviation (e.g. IFF)
        tag (str): tag modifier abbreviation (e.g. /IFF)

    Example:
        >>> from tagsmgr import TagModifier
        >>> iff = TagModifier(name='Issue For Fabrication', abbrev='IFF')
        >>> ifc = TagModifier(name='Issue For Construction', abbrev='IFC')
        >>> ifc = iff
        False
    """

    def __init__(self, name, abbrev, color):
        self.name = name + ' ({})'.format(abbrev)
        self.abbrev = abbrev
        self.color = color

    @property
    def tag(self):
        """Tag string (e.g. /IFF)"""
        return '{}{}'.format(tagscfg.TAG_MODIFIER_MARKER, self.abbrev)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<{} name={}>'.format(self.__class__.__name__, self.name)

    def __hash__(self):
        return hash(self.tag)

    def __eq__(self, other):
        return self.tag == other.tag

    def __lt__(self, other):
        return self.tag < other.tag


class TagModifiers(object):
    """Static class representing standard implemented modifiers.

    This class also has helper functions related to tag modifiers.

    Example:
        >>> from tagsmgr import TagModifier, TagModifiers
        >>> iff = TagModifier(name='Issue For Fabrication', abbrev='IFF')
        >>> TagModifiers.has_modifier('TAG /IFF', iff)
        True
        >>> TagModifiers.extract_modifiers('TAG /IFF')
        [<TagModifier name=Issue For Fabrication>]
    """

    @classmethod
    def get_modifiers(cls):
        """Return a list of currently implemented modifiers."""
        modifs = tagscfg.get_modifier_defs()
        return {
            TagModifier(
                abbrev=tagmod_def.abbrev,
                name=tagmod_def.abbrev,
                color=tagmod_def.color
            )
            for tagmod_def in modifs
        }

    @classmethod
    def get_modifier_names(cls):
        """Return a list of names of currently implemented modifiers."""
        return [x.name for x in cls.get_modifiers()]

    @classmethod
    def extract_modifiers(cls, tag_str):
        """Extract modifiers from tag string.

        Args:
            tag_str (str): tag string (e.g. 'TAG /IFF')

        Returns:
            list[TagModifier]: list of extracted tag modifiers

        Example:
            >>> from tagsmgr import TagModifiers
            >>> TagModifiers.extract_modifiers('TAG /IFF')
            [<TagModifier name=Issue For Fabrication>]
        """
        return [x for x in cls.get_modifiers() if x.tag in tag_str]

    @classmethod
    def clean_modifiers(cls, tag_str):
        """Remove modifiers from tag string.

        Args:
            tag_str (str): tag string (e.g. 'TAG /IFF')

        Returns:
            str: cleaned tag string

        Example:
            >>> from tagsmgr import TagModifiers
            >>> TagModifiers.clean_modifiers('TAG /IFF')
            'TAG'
        """
        cleaned = tag_str
        for mod in cls.get_modifiers():
            cleaned = cleaned.replace(mod.tag, '')
        return cleaned.strip()

    @classmethod
    def has_modifier(cls, tag_str, modifier):
        """Check whether tag string contains the specified modifier.

        Args:
            tag_str (str): tag string (e.g. 'TAG /IFF')
            modifier (TagModifier): tag modifier

        Returns:
            bool: True if tag string contains the specified modifier

        Example:
            >>> from tagsmgr import TagModifiers
            >>> iff = TagModifier(name='Issue For Fabrication',
            ...                   abbrev='IFF')
            >>> TagModifiers.has_modifier('TAG /IFF', iff)
            True
        """
        return modifier in cls.extract_modifiers(tag_str)

    @classmethod
    def has_modifier_tags(cls, tag_str):
        """Check whether tag string contains any modifiers.

        Args:
            tag_str (str): tag string (e.g. 'TAG /IFF')

        Returns:
            bool: True if tag string contains at least one modifier
        """
        return len(cls.extract_modifiers(tag_str)) > 0

    @classmethod
    def add_modifier(cls, tag_str, modifier):
        """Add a modifier to the given tag string.

        Args:
            tag_str (str): tag string (e.g. 'TAG /IFF')
            modifier (TagModifier): tag modifier

        Returns:
            str: updated tag string

        Example:
            >>> from tagsmgr import TagModifiers
            >>> iff = TagModifier(name='Issue For Fabrication',
            ...                   abbrev='IFF')
            >>> TagModifiers.add_modifier('TAG', iff)
            'TAG /IFF'
        """
        if not cls.has_modifier(tag_str, modifier):
            return tagscfg.TAG_MODIFIER_DELIMITER.join([tag_str, modifier.tag])
        else:
            return tag_str

    @classmethod
    def remove_modifier(cls, tag_str, modifier):
        """Remove a modifier from the given tag string.

        Args:
            tag_str (str): tag string (e.g. 'TAG /IFF')
            modifier (TagModifier): tag modifier

        Returns:
            str: updated tag string

        Example:
            >>> from tagsmgr import TagModifiers
            >>> iff = TagModifier(name='Issue For Fabrication',
            ...                     abbrev='IFF')
            >>> TagModifiers.remove_modifier('TAG /IFF /IFC', iff)
            'TAG /IFC'
        """
        return tag_str.replace(
            tagscfg.TAG_MODIFIER_DELIMITER.join(['', modifier.tag]),
            ''
            ).strip()


class Tag(object):
    """Class respresenting a tag.

    This class implements __eq__, __lt__, and __hash__ for direct comparision,
    inclusion tests, and to be included in hashtables e.g. sets

    Args:
        tag_str (str):
            sting to initiate a tag from; can not include tag modifiers

    Attributes:
        name (str): tag name
        modifiers (list[TagModifier]): list of applied tag modifiers
        id (str): tag id; original tag_str in current implementation
    """

    def __init__(self, tag_str):
        self._tag_str = tag_str

    def __str__(self):
        return self._tag_str

    def __repr__(self):
        return '<{} name={}>'.format(self.__class__.__name__, self._tag_str)

    def __hash__(self):
        return hash(self._tag_str)

    def __eq__(self, other):
        if isinstance(other, Tag):
            return self.name == other.name \
                    and pyutils.compare_lists(self.modifiers, other.modifiers)
        elif isinstance(other, str):
            return self.name == other.name

    def __lt__(self, other):
        return self.name < other.name

    @property
    def name(self):
        return TagModifiers.clean_modifiers(self._tag_str)

    @property
    def modifiers(self):
        return TagModifiers.extract_modifiers(self._tag_str)

    @property
    def tagid(self):
        return self._tag_str

    def is_valid(self):
        """Check whether tag name and modifiers are valid."""
        return tagscfg.TAG_DELIMITER not in self._tag_str \
            and tagscfg.TAG_MODIFIER_MARKER not in self._tag_str

    def rename(self, new_name):
        """Rename tag.

        Args:
            new_name (str): new tag name
        """
        self._tag_str = self._tag_str.replace(self.name, new_name)

    def add_modifier(self, modifier):
        """Add modifier to tag.

        Args:
            modifier (TagModifier): modifier to add to tag
        """
        self._tag_str = TagModifiers.add_modifier(self._tag_str, modifier)

    def remove_modifier(self, modifier):
        """Remove modifier from tag.

        Args:
            modifier (TagModifier): modifier to remove to tag
        """
        self._tag_str = TagModifiers.remove_modifier(self._tag_str, modifier)


class TagCollection(object):
    """Class representing a collection of tags.

    Args:
        tags ([Tag]): list of tag objects create a collection from

    Attributes:
        names (str): string representing names of contained tags
        tagids (str): string representing ids of contained tags
    """

    def __init__(self, tags):
        self._tags = tags

    def __str__(self):
        return self.tagids

    @property
    def names(self):
        return tagscfg.TAG_DELIMITER.join([x.name for x in self._tags])

    @property
    def tagids(self):
        return tagscfg.TAG_DELIMITER.join([x.tagid for x in self._tags])


def _get_tag_param(element):
    return element.LookupParameter(tagscfg.get_tags_param())


def _get_tag_paramid():
    # get shared param id
    param_id = revit.query.get_sharedparam_id(tagscfg.get_tags_param())
    if not param_id:
        raise PyRevitException('Can not find tags shared param.')
    return param_id


def get_last_metadata():
    """Get the metadata dict.

    Tag manager functions may retain metadata about their operations.
    As an example, :func:`get_available_tags` saves the number or processed
    elements in the metadata dict. After each operation, the metadata dict
    could be received from this method and analysed.

    Example:
        >>> import tagsmgr
        >>> # get_available_tags stores no of elements processed as metadata
        >>> tags = tagmgr.get_available_tags()
        >>> tagmgr.get_last_metadata()
        {'count': 201237 }
    """
    global _METADATA_DICT
    return _METADATA_DICT


def extract_tags(element):
    """Extarct tags from given element.

    This method, reads the tag shared parameter value on this element and
    determines the tags applied to it.

    Args:
        element (DB.Element): element to extract the tags from

    Returns:
        set(Tag): set of tags on the given element

    Example:
        >>> import tagsmgr
        >>> tagmgr.extract_tags(selected_element)
        set([<Tag object at 0x0000000000000252>])
    """
    tags = set()
    tagparam = _get_tag_param(element)
    if tagparam:
        val = tagparam.AsString()
        if val:
            tags.update(extract_tags_from_str(str(val)))
    return tags


def extract_tags_from_str(tag_str):
    """Extarct tags from given tag string.

    Args:
        element (DB.Element): element to extract the tags from

    Returns:
        set[Tag]: set of tags on the given element

    Example:
        >>> import tagsmgr
        >>> tagmgr.extract_tags_from_str('SOME_SCOPE_ID /IFF')
        set([<Tag object at 0x0000000000000252>])
    """
    tags = set()
    if tag_str and not tag_str.isspace():
        cleaned = [x.strip()
                   for x in tag_str.split(tagscfg.TAG_DELIMITER)]
        tags.update([Tag(x) for x in cleaned])
    return tags


def join_tags(tags):
    """Join multiple tags into a TagCollection.

    Args:
        tags (list[Tag]): list of tags to be joined

    Returns:
        TagCollection: tag collection containing given tags
    """
    return TagCollection(tags)


def get_all_tag_elements(tag):
    """Get all elements of given tag.

    Args:
        tag (Tag): tag object

    Returns:
        list[DB.Element]: list of elements in that tag
    """
    # does not work in < 2016
    # spid = framework.Guid('24353a46-1313-46a4-a779-d33ffe9353ab')
    # pid = DB.SharedParameterElement.Lookup(revit.doc, spid)
    # pp = DB.ParameterValueProvider(pid)
    # pe = DB.FilterStringEquals()
    # vrule = DB.FilterDoubleRule(pp, pe, tag_id, True)
    # param_filter = DB.ElementParameterFilter(vrule)
    # elements = DB.FilteredElementCollector(revit.doc) \
    #           .WherePasses(param_filter) \
    #           .ToElementIds()
    skip_cats = [query.get_category(x) for x in SCOPE_SKIP_CATEGORIES]
    skip_catids = [x.Id for x in skip_cats if x is not None]
    return [x for x in query.get_all_elements()
            if tag in extract_tags(x)
            and x.Category is not None
            and x.Category.Id not in skip_catids]


def get_available_tags(elements=None):
    """Get tags used in current model or on a list of elements.

    Args:
        elements (list[DB.Element], optional):
            list of elements to filer by tag.

    Returns:
        set[Tag]: set of tags in model or on elements
    """
    global _METADATA_DICT
    target_elements = \
        elements \
        or query.get_elements_by_shared_parameter(
            param_name=tagscfg.get_tags_param(),
            param_value="",
            inverse=True,
            doc=revit.doc
            )
    tags = set()
    for element in target_elements:
        tags.update(extract_tags(element))
    # record metadata
    _METADATA_DICT = {'count': len(target_elements)}
    return sorted(tags)


def is_tag_available(tag):
    all_tags = get_available_tags()
    return tag.name in [x.name for x in all_tags]


def select_tag_elements(tags):
    """Select elements of the given tag.

    Args:
        tag (Tag): tag object
    """
    elements = []
    for tag in tags:
        elements.extend(get_all_tag_elements(tag))
    revit.get_selection().set_to(elements)


def apply_tags(element, tags, config=None):
    """Apply given tags to given element. Use configuration if provided.

    Args:
        element (DB.Element): element to apply the tags to
        tags (list[Tag]): list of tags to be applied to element
        config (ApplyTagsConfig, optional): apply tag configuration,
            defaults to ApplyTagsConfig(append=False, circuits=True)

    Example:
        >>> import tagsmgr
        >>> cfg = tagmgr.ApplyTagsConfig(append=True, circuits=False)
        >>> tagmgr.apply_tags(element, tag_list, config=cfg)
    """
    if not config:
        config = ApplyTagsConfig(append=False, circuits=True)
        mlogger.debug('Using default config %s', config)

    # process elements that are somehow associated with this element
    # process elements in a group
    if isinstance(element, DB.Group):
        mlogger.debug('Applying tag to group members...')
        for el_id in element.GetMemberIds():
            apply_tags(revit.doc.GetElement(el_id), tags, config=config)
    # process connected circuits
    elif isinstance(element, DB.FamilyInstance) \
            and config.circuits:
        mlogger.debug('Applying tag to circuits...')
        esystems = query.get_connected_circuits(element,
                                                space=False,
                                                spare=False)
        if esystems:
            for esys in esystems:
                apply_tags(esys, tags, config=config)

    if config.append:
        el_tags = extract_tags(element)
        el_tags.update(tags)
        mlogger.debug('Appending tags %s', el_tags)
    else:
        el_tags = set(tags)
        mlogger.debug('Replacing tags with %s', el_tags)

    sparam = _get_tag_param(element)
    if sparam:
        mlogger.debug('Tag param found. Existing value: %s', sparam.AsString())
        tag_col = join_tags(el_tags)
        mlogger.debug('New value: %s', tag_col.tagids)
        sparam.Set(tag_col.tagids)


def match_tags(src_element, dest_elements):
    """Apply tags from source element to another element.

    Args:
        src_element (DB.Element): element with source tags
        dest_elements (DB.Element): elements to apply the source tags to
    """
    tags = extract_tags(src_element)
    for delement in dest_elements:
        apply_tags(delement, tags)


def add_modifier(tags, tag_modifier, elements=None):
    """Add a modifier to list of tags.

    Args:
        tags (list[Tag]): list of target tags
        tag_modifier (TagModifier): tag modifier to apply to tags
        elements (list[DB.Element], optional):
            set of elements to rename the tag.
    """
    for tag in tags:
        target_elements = elements or get_all_tag_elements(tag)
        for element in target_elements:
            el_tags = list(extract_tags(element))
            extag_idx = el_tags.index(tag)
            el_tags[extag_idx].add_modifier(tag_modifier)
            apply_tags(element, el_tags)


def remove_modifier(tags, tag_modifier, elements=None):
    """Remove a modifier from list of tags.

    Args:
        tags (list[Tag]): list of target tags
        tag_modifier (TagModifier):
            tag modifier to be removed from tags
        elements (list[DB.Element], optional):
            set of elements to rename the tag.
    """
    for tag in tags:
        target_elements = elements or get_all_tag_elements(tag)
        for element in target_elements:
            el_tags = list(extract_tags(element))
            extag_idx = el_tags.index(tag)
            el_tags[extag_idx].remove_modifier(tag_modifier)
            apply_tags(element, el_tags)


def rename_tag(tag, new_tag_name, elements=None):
    """Rename a tag id in model or on a set of elements.

    Args:
        tag (Tag): tag to be renamed
        new_tag_name (str): new tag identifier
        elements (list[DB.Element], optional):
            set of elements to rename the tag.

    Raises:
        PyRevitException: invalid tag name

    Examples:
        >>> import tagsmgr
        >>> tagmgr.rename_tag(tag, 'NEW_SCOPE')

        >>> tagmgr.rename_tag(tag, 'NEW_SCOPEA,SCOPEB')
        Traceback (most recent call last):
            File "<stdin>", line 1, in <module>
        PyRevitException: Invalid Tag Name
    """
    newtag = Tag(new_tag_name)
    if newtag.is_valid():
        if is_tag_available(newtag):
            raise PyRevitException('New tag name already exists.')

        target_elements = elements or get_all_tag_elements(tag)
        for element in target_elements:
            el_tags = list(extract_tags(element))
            extag_idx = el_tags.index(tag)
            el_tags[extag_idx].rename(new_tag_name)
            apply_tags(element, el_tags)
    else:
        raise PyRevitException('Invalid Tag Name')


def remove_tag(tag, elements=None):
    """Remove a tag id from model or from a set of elements.

    Args:
        tag (Tag): tag to be removed
        elements (list[DB.Element], optional):
            set of elements to remove the tag from.

    Examples:
        >>> import tagsmgr
        >>> tagmgr.remove_tag(tag)
    """
    target_elements = elements or get_all_tag_elements(tag)
    for element in target_elements:
        el_tags = extract_tags(element)
        if tag in el_tags:
            el_tags.remove(tag)
            apply_tags(element, el_tags)


def clear_tags(elements=None):
    """Clear all tags from model or set of elements.

    Args:
        elements (list[DB.Element], optional):
            set of elements to remove the tag from.
    """
    target_elements = elements or query.get_all_elements()
    for element in target_elements:
        apply_tags(element, [])


def create_tag_filter(tags, name_format=None, exclude=False):
    """Create standard rule-based filters for given tags (max of 3 tags).

    Args:
        tags (list[Tag]): list of tags to create filter for (max of 3)
        name_format (str, optional): format for naming the filter,
            must include `{all_or_none}` and `{tag_names}`.
        exclude (bool, optional): create exclusion filter, defaults to False

    Returns:
        list[DB.ParameterFilterElement]: list of created filters

    Example:
        >>> import tagsmgr
        >>> fname = 'CUSTOM {all_or_none} FILTER FOR {tag_names}'
        >>> tag_filters = tagmgr.create_tag_filter(tags,
        ...                                              name_format=fname,
        ...                                              exclude=True)
        [<Autodesk.Revit.DB.ParameterFilterElement object at ...>,
        <Autodesk.Revit.DB.ParameterFilterElement object at ...>]
    """
    sfilters = []
    # create filter name and check availability
    tags_col = join_tags(tags)
    if not name_format:
        name_format = tagscfg.TAG_FILTER_NAMING
    filter_name = name_format.format(all_or_none='NONE' if exclude else 'ALL',
                                     tag_names=tags_col.names)
    for exst_filter in revit.query.get_rule_filters():
        if exst_filter.Name == filter_name:
            sfilters.append(exst_filter)
            return sfilters

    # get shared param id
    param_id = _get_tag_paramid()

    # create filter rule
    rules = framework.List[DB.FilterRule]()
    param_prov = DB.ParameterValueProvider(param_id)
    param_contains = DB.FilterStringContains()
    for tag in tags:
        rule = DB.FilterStringRule(param_prov,
                                   param_contains,
                                   tag.name,
                                   False)
        if exclude:
            rule = DB.FilterInverseRule(rule)
        rules.Add(rule)

    # collect applicable categories
    cats = []
    for cat in revit.query.get_all_category_set():
        if DB.ParameterFilterElement.AllRuleParametersApplicable(
                revit.doc,
                framework.List[DB.ElementId]([cat.Id]),
                rules
            ):
            cats.append(cat.Id)

    # create filter
    sfilter = \
        DB.ParameterFilterElement.Create(revit.doc,
                                         filter_name,
                                         framework.List[DB.ElementId](cats),
                                         rules)
    sfilters.append(sfilter)
    return sfilters


def create_modifier_filters(exclude=False):
    """Create standard rule-based filters for available tag modifiers.

    Args:
        exclude (bool, optional): create exclusion filter, defaults to False

    Returns:
        list[DB.ParameterFilterElement]: list of created filters
    """
    mfilters = []

    existing_filters = [x for x in revit.query.get_rule_filters()]

    for modif in TagModifiers.get_modifiers():
        # create filter name and check availability
        filter_name = \
            '{} {}'.format('NONE' if exclude else 'ALL', modif.name)
        filter_exists = False
        for exst_filter in existing_filters:
            if exst_filter.Name == filter_name:
                filter_exists = True
                mfilters.append(exst_filter)
        if filter_exists:
            continue

        # get shared param id
        param_id = _get_tag_paramid()

        # create filter rule
        rules = framework.List[DB.FilterRule]()
        param_prov = DB.ParameterValueProvider(param_id)
        param_contains = DB.FilterStringContains()
        rule = DB.FilterStringRule(param_prov,
                                   param_contains,
                                   modif.tag,
                                   False)
        if exclude:
            rule = DB.FilterInverseRule(rule)
        rules.Add(rule)

        # collect applicable categories
        cats = []
        for cat in revit.query.get_all_category_set():
            if DB.ParameterFilterElement.AllRuleParametersApplicable(
                    revit.doc,
                    framework.List[DB.ElementId]([cat.Id]),
                    rules
                ):
                cats.append(cat.Id)

        # create filter
        mfilter = DB.ParameterFilterElement.Create(
            revit.doc,
            filter_name,
            framework.List[DB.ElementId](cats),
            rules
            )
        mfilters.append(mfilter)
    return mfilters


def create_tag_schedule(tag, category, src_schedule):
    """Create a schedule, listing elements of the given tag and category.

    Args:
        tag (Tag): tag to create schedule for
        category (DB.Category): element category to filter the elements by
        src_schedule (DB.ViewSchedule):
            source schedule to match style and schema

    Returns:
        DB.ViewSchedule: newly created schedule
    """
    doc = src_schedule.Document
    newsched_name = '{} ({})'.format(tag.name, category.Name)
    newsched = query.get_view_by_name(newsched_name)
    if not newsched:
        newsched_id = src_schedule.Duplicate(DB.ViewDuplicateOption.Duplicate)
        newsched = doc.GetElement(newsched_id)
    if newsched:
        param_id = _get_tag_paramid()
        tagfield = query.get_schedule_field(newsched, tagscfg.get_tags_param())
        if not tagfield:
            tagfield = \
                newsched.Definition.AddField(DB.ScheduleFieldType.Instance,
                                             param_id)
        tagfield.IsHidden = True

        tagfilter_indices = \
            query.get_schedule_filters(newsched,
                                       tagscfg.get_tags_param(),
                                       return_index=True)
        if tagfilter_indices:
            for idx in tagfilter_indices:
                newsched.Definition.RemoveFilter(idx)

        tagfilter = DB.ScheduleFilter(tagfield.FieldId,
                                      DB.ScheduleFilterType.Contains,
                                      tag.name)
        newsched.Definition.AddFilter(tagfilter)
        newsched.ViewName = newsched_name
        return newsched


def create_tag_3dview(tags):
    """Create 3d view filtering elements of given tags (max 3 tags).

    Args:
        tags (list[Tag]): list of tags to filter the view by (max of 3)

    Returns:
        DB.View3D: newly created 3d view
    """
    # create necessary filters
    mfilters = create_tag_filter(tags, exclude=True)

    if mfilters:
        tags_col = join_tags(tags)
        view_name = '{} ({})'.format(tagscfg.TAGVIEW_PREFIX,
                                     tags_col.names)
        # create 3d view
        tag_view = create.create_3d_view(view_name, doc=revit.doc)
        # clean all existing filters
        for viewfilterid in tag_view.GetFilters():
            tag_view.RemoveFilter(viewfilterid)
        # add the modifier filters
        for mfilter in mfilters:
            tag_view.AddFilter(mfilter.Id)
            # set filter visibility
            tag_view.SetFilterVisibility(mfilter.Id, False)

        # setup other view configs
        tag_view.AreImportCategoriesHidden = True
        tag_view.AreAnnotationCategoriesHidden = True
        tag_view.AreCoordinationModelHandlesHidden = True
        tag_view.ArePointCloudsHidden = True

        return tag_view

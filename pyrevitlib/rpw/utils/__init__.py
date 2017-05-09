def get_all_subclasses(parent_class):
    sub_classes = []
    if hasattr(parent_class, '__subclasses__'):
        derived_classes = parent_class.__subclasses__()
        sub_classes.extend(derived_classes)
        for derived_class in derived_classes:
            subsub_classes = get_all_subclasses(derived_class)
            sub_classes.extend(subsub_classes)
    return sub_classes


def make_canonical_name(*args):
    return '.'.join(args)

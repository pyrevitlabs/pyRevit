def write(data_key, msg):
    # Get the StringStringMap class which can write data into.
    # noinspection PyUnresolvedReferences
    data_map = __commandData__.JournalData
    data_map.Clear()

    # Begin to add the support data
    data_map.Add(data_key, msg)


def read(data_key):
    # Get the StringStringMap class which can write data into.
    # noinspection PyUnresolvedReferences
    data_map = __commandData__.JournalData

    # Begin to get the support data
    return data_map[data_key]

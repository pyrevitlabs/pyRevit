__all__ = [ 'pyRevitVersion']

class pyRevitVersion:
    """Contains current pyRevit version"""
    major = 3
    minor = 0
    patch = 0
    
    @staticmethod
    def as_int_tuple():
        """Returnx version as an int tuple (major, minor, patch)"""
        return (pyRevitVersion.major, pyRevitVersion.minor, pyRevitVersion.patch)

    @staticmethod
    def as_str_tuple():
        """Returnx version as an string tuple ('major', 'minor', 'patch')"""
        return (str(pyRevitVersion.major), str(pyRevitVersion.minor), str(pyRevitVersion.patch))

    @staticmethod
    def full_version_as_str():
        """Returnx 'major.minor.patch' in string"""
        return str(pyRevitVersion.major) + '.' + str(pyRevitVersion.minor) + '.' +  str(pyRevitVersion.patch)

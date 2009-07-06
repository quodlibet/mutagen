import mutagen.mp4

from mutagen import Metadata
from mutagen._util import DictMixin, dict_match
from mutagen.mp4 import MP4, MP4Tags, error, delete

__all__ = ["EasyMP4Tags", "EasyMP4", "delete", "error"]

class EasyMP4KeyError(error, KeyError, ValueError):
    pass

class EasyMP4Tags(DictMixin, Metadata):
    """A file with MPEG-4 iTunes metadata.

    Like Vorbis comments, EasyMP4Tags keys are case-insensitive ASCII
    strings, and values are a list of Unicode strings (and these lists
    are always of length 0 or 1). If you need access to the full MP4
    metadata feature set, you should use MP4, not EasyMP4.
    """

    Set = {}
    Get = {}
    Delete = {}
    List = {}

    def __init__(self, *args, **kwargs):
        self.__mp4 = MP4Tags(*args, **kwargs)
        self.load = self.__mp4.load
        self.save = self.__mp4.save
        self.delete = self.__mp4.delete

    filename = property(lambda s: s.__mp4.filename,
                        lambda s, fn: setattr(s.__mp4, 'filename', fn))

    def RegisterKey(cls, key,
                    getter=None, setter=None, deleter=None, lister=None):
        """Register a new key mapping.

        A key mapping is four functions, a getter, setter, deleter,
        and lister. The key may be either a string or a glob pattern.

        The getter, deleted, and lister receive an MP4Tags instance
        and the requested key name. The setter also receives the
        desired value, which will be a list of strings.

        The getter, setter, and deleter are used to implement __getitem__,
        __setitem__, and __delitem__.

        The lister is used to implement keys(). It should return a
        list of keys that are actually in the MP4 instance, provided
        by its associated getter.
        """
        key = key.lower()
        if getter is not None:
            cls.Get[key] = getter
        if setter is not None:
            cls.Set[key] = setter
        if deleter is not None:
            cls.Delete[key] = deleter
        if lister is not None:
            cls.List[key] = lister
    RegisterKey = classmethod(RegisterKey)

    def RegisterTextKey(cls, key, atomid):
        """Register a text key.

        If the key you need to register is a simple one-to-one mapping
        of MP4 atom name to EasyMP4Tags key, then you can use this
        function:
            EasyMP4Tags.RegisterTextKey("artist", "\xa9ART")
        """
        def getter(tags, key):
            return tags[atomid]

        def setter(tags, key, value):
            tags[atomid] = value

        def deleter(mp4, key):
            del(mp4[atomid])

        cls.RegisterKey(key, getter, setter, deleter)
    RegisterTextKey = classmethod(RegisterTextKey)

    def __getitem__(self, key):
        key = key.lower()
        func = dict_match(self.Get, key)
        if func is not None:
            return func(self.__mp4, key)
        else:
            raise EasyMP4KeyError("%r is not a valid key" % key)

    def __setitem__(self, key, value):
        key = key.lower()
        if isinstance(value, basestring):
            value = [value]
        func = dict_match(self.Set, key)
        if func is not None:
            return func(self.__mp4, key, value)
        else:
            raise EasyMP4KeyError("%r is not a valid key" % key)

    def __delitem__(self, key):
        key = key.lower()
        func = dict_match(self.Delete, key)
        if func is not None:
            return func(self.__mp4, key)
        else:
            raise EasyMP4KeyError("%r is not a valid key" % key)

    def keys(self):
        keys = []
        for key in self.Get.keys():
            if key in self.List:
                keys.extend(self.List[key](self.__mp4, key))
            elif key in self:
                keys.append(key)
        return keys

    def pprint(self):
        """Print tag key=value pairs."""
        strings = []
        for key in sorted(self.keys()):
            values = self[key]
            for value in values:
                strings.append("%s=%s" % (key, value))
        return "\n".join(strings)

for atomid, key in {
    '\xa9nam': 'title',
    '\xa9alb': 'album',
    '\xa9ART': 'artist',
    'aART': 'albumartist',
    '\xa9day': 'date',
    '\xa9cmt': 'comment',
    'desc': 'description',
    '\xa9grp': 'grouping',
    '\xa9grn': 'genre',
    'cprt': 'copyright',
    'soal': 'albumsort',
    'soaa': 'albumartistsort',
    'soar': 'artistsort',
    'sonm': 'titlesort',
    'soco': 'composersort',
    }.items():
    EasyMP4Tags.RegisterTextKey(key, atomid)

class EasyMP4(MP4):
    """Like MP4, but uses EasyMP4Tags for tags."""
    MP4Tags = EasyMP4Tags

    Get = EasyMP4Tags.Get
    Set = EasyMP4Tags.Set
    Delete = EasyMP4Tags.Delete
    List = EasyMP4Tags.List
    RegisterTextKey = EasyMP4Tags.RegisterTextKey
    RegisterKey = EasyMP4Tags.RegisterKey

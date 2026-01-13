# Copyright (C) 2009  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from collections.abc import Callable
from typing import Final, override

from mutagen import Tags
from mutagen._util import DictMixin, dict_match
from mutagen.mp4 import MP4, MP4Info, MP4Tags, delete, error

__all__ = ["EasyMP4Tags", "EasyMP4", "delete", "error"]


class EasyMP4KeyError(error, KeyError, ValueError):
    pass

type Getter = Callable[[MP4Tags, str], list[str]]
type Setter = Callable[[MP4Tags, str, list[str]], None]
type Deleter = Callable[[MP4Tags, str], None]
type Lister = Callable[[MP4Tags, str], list[str]]

class EasyMP4Tags(DictMixin, Tags):
    """EasyMP4Tags()

    A file with MPEG-4 iTunes metadata.

    Like Vorbis comments, EasyMP4Tags keys are case-insensitive ASCII
    strings, and values are a list of Unicode strings (and these lists
    are always of length 0 or 1).

    If you need access to the full MP4 metadata feature set, you should use
    MP4, not EasyMP4.
    """

    Set: dict[str, Setter] = {}
    Get: dict[str, Getter] = {}
    Delete: dict[str, Deleter] = {}
    List: dict[str, Lister] = {}

    __mp4: MP4Tags
    load: Callable[..., None]
    save: Callable[..., None]
    delete: Callable[..., None]

    def __init__(self, *args, **kwargs):
        self.__mp4 = MP4Tags(*args, **kwargs)
        self.load = self.__mp4.load
        self.save = self.__mp4.save
        self.delete = self.__mp4.delete

    @property
    def filename(self) -> str | None:
        return self.__mp4.filename

    @filename.setter
    def filename(self, fn: str):
        self.__mp4.filename = fn

    @property
    def _padding(self):
        return self.__mp4._padding

    @classmethod
    def RegisterKey(cls, key: str,
                    getter: Getter | None=None, setter: Setter | None=None, deleter: Deleter | None =None, lister: Lister | None=None):
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

    @classmethod
    def RegisterTextKey(cls, key: str, atomid: str):
        """Register a text key.

        If the key you need to register is a simple one-to-one mapping
        of MP4 atom name to EasyMP4Tags key, then you can use this
        function::

            EasyMP4Tags.RegisterTextKey("artist", "\xa9ART")
        """
        def getter(tags: MP4Tags, key: str) -> list[str]:
            return tags[atomid]

        def setter(tags: MP4Tags, key: str, value: list[str]) -> None:
            tags[atomid] = value

        def deleter(tags: MP4Tags, key: str) -> None:
            del tags[atomid]

        cls.RegisterKey(key, getter, setter, deleter)

    @classmethod
    def RegisterIntKey(cls, key: str, atomid: str, min_value: int=0, max_value: int=(2 ** 16) - 1):
        """Register a scalar integer key.
        """

        def getter(tags: MP4Tags, key: str):
            return list(map(str, tags[atomid]))

        def setter(tags: MP4Tags, key: str, value: list[str]):
            clamp = lambda x: int(min(max(min_value, x), max_value))
            tags[atomid] = [clamp(v) for v in map(int, value)]

        def deleter(tags: MP4Tags, key: str):
            del tags[atomid]

        cls.RegisterKey(key, getter, setter, deleter)

    @classmethod
    def RegisterIntPairKey(cls, key: str, atomid: str, min_value: int=0,
                           max_value: int=(2 ** 16) - 1):
        def getter(tags: MP4Tags, key: str):
            ret: list[str] = []
            for (track, total) in tags[atomid]:
                if total:
                    ret.append("%d/%d" % (track, total))
                else:
                    ret.append(str(track))
            return ret

        def setter(tags: MP4Tags, key: str, value: list[str]):
            clamp = lambda x: int(min(max(min_value, x), max_value))
            data: list[tuple[int, int]] = []
            for v in value:
                try:
                    trackss, totals = v.split("/")
                    tracks = clamp(int(trackss))
                    total = clamp(int(totals))
                except (ValueError, TypeError):
                    tracks = clamp(int(v))
                    total = min_value
                data.append((tracks, total))
            tags[atomid] = data

        def deleter(tags: MP4Tags, key: str):
            del tags[atomid]

        cls.RegisterKey(key, getter, setter, deleter)

    @classmethod
    def RegisterFreeformKey(cls, key: str, name: str, mean: str="com.apple.iTunes"):
        """Register a text key.

        If the key you need to register is a simple one-to-one mapping
        of MP4 freeform atom (----) and name to EasyMP4Tags key, then
        you can use this function::

            EasyMP4Tags.RegisterFreeformKey(
                "musicbrainz_artistid", "MusicBrainz Artist Id")
        """
        atomid = "----:" + mean + ":" + name

        def getter(tags: MP4Tags, key: str) -> list[str]:
            return [s.decode("utf-8", "replace") for s in tags[atomid]]

        def setter(tags: MP4Tags, key: str, value: list[str]) -> None:
            encoded: list[bytes] = []
            for v in value:
                if not isinstance(v, str):  # pyright: ignore[reportUnnecessaryIsInstance]
                    raise TypeError(f"{v!r} not str")
                encoded.append(v.encode("utf-8"))
            tags[atomid] = encoded

        def deleter(tags: MP4Tags, key: str):
            del tags[atomid]

        cls.RegisterKey(key, getter, setter, deleter)

    def __getitem__(self, key: str):
        key = key.lower()
        func = dict_match(self.Get, key)
        if func is not None:
            return func(self.__mp4, key)
        else:
            raise EasyMP4KeyError(f"{key!r} is not a valid key")

    def __setitem__(self, key: str, value: list[str] | str):
        key = key.lower()

        if isinstance(value, str):
            value = [value]

        func = dict_match(self.Set, key)
        if func is not None:
            return func(self.__mp4, key, value)
        else:
            raise EasyMP4KeyError(f"{key!r} is not a valid key")

    def __delitem__(self, key: str):
        key = key.lower()
        func = dict_match(self.Delete, key)
        if func is not None:
            return func(self.__mp4, key)
        else:
            raise EasyMP4KeyError(f"{key!r} is not a valid key")

    def keys(self):
        keys: list[str] = []
        for key in self.Get:
            if key in self.List:
                keys.extend(self.List[key](self.__mp4, key))
            elif key in self:
                keys.append(key)
        return keys

    @override
    def pprint(self):
        """Print tag key=value pairs."""
        strings: list[str] = []
        for key in sorted(self.keys()):
            values = self[key]
            for value in values:
                strings.append(f"{key}={value}")
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
    '\xa9gen': 'genre',
    'cprt': 'copyright',
    'soal': 'albumsort',
    'soaa': 'albumartistsort',
    'soar': 'artistsort',
    'sonm': 'titlesort',
    'soco': 'composersort',
}.items():
    EasyMP4Tags.RegisterTextKey(key, atomid)

for name, key in {
    'MusicBrainz Artist Id': 'musicbrainz_artistid',
    'MusicBrainz Track Id': 'musicbrainz_trackid',
    'MusicBrainz Album Id': 'musicbrainz_albumid',
    'MusicBrainz Album Artist Id': 'musicbrainz_albumartistid',
    'MusicIP PUID': 'musicip_puid',
    'MusicBrainz Album Status': 'musicbrainz_albumstatus',
    'MusicBrainz Album Type': 'musicbrainz_albumtype',
    'MusicBrainz Release Country': 'releasecountry',
}.items():
    EasyMP4Tags.RegisterFreeformKey(key, name)

for name, key in {
    "tmpo": "bpm",
}.items():
    EasyMP4Tags.RegisterIntKey(key, name)

for name, key in {
    "trkn": "tracknumber",
    "disk": "discnumber",
}.items():
    EasyMP4Tags.RegisterIntPairKey(key, name)


class EasyMP4(MP4):
    """EasyMP4(filelike)

    Like :class:`MP4 <mutagen.mp4.MP4>`, but uses :class:`EasyMP4Tags` for
    tags.

    Attributes:
        info (`mutagen.mp4.MP4Info`)
        tags (`EasyMP4Tags`)
    """

    MP4Tags: Final = EasyMP4Tags  # type: ignore

    Get: Final = EasyMP4Tags.Get
    Set: Final = EasyMP4Tags.Set
    Delete: Final = EasyMP4Tags.Delete
    List: Final = EasyMP4Tags.List
    RegisterTextKey: Final = EasyMP4Tags.RegisterTextKey
    RegisterKey: Final = EasyMP4Tags.RegisterKey

    info: MP4Info
    tags: EasyMP4Tags

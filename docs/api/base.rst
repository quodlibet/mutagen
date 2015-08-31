Main Module
-----------

.. automodule:: mutagen
    :members: File, version, version_string


Base Classes
~~~~~~~~~~~~

.. class:: text()

    This type only exists for documentation purposes. It represents
    :obj:`unicode` under Python 2 and :obj:`str` under Python 3.


.. autoclass:: mutagen.FileType(filename)
    :members: pprint, add_tags, mime
    :show-inheritance:

    .. automethod:: delete()

    .. automethod:: save()


.. autoclass:: mutagen.Metadata

    .. automethod:: delete()

    .. automethod:: save()


.. autoclass:: mutagen.StreamInfo
    :members: pprint


.. autoclass:: mutagen.PaddingInfo()
    :members:


.. autoclass:: mutagen.MutagenError


Internal Classes
~~~~~~~~~~~~~~~~

.. automodule:: mutagen._util

.. autoclass:: mutagen._util.DictMixin

.. autoclass:: mutagen._util.DictProxy
    :show-inheritance:

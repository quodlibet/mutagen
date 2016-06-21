Main Module
-----------

.. automodule:: mutagen
    :members: File, version, version_string


Base Classes
~~~~~~~~~~~~

.. autoclass:: mutagen.FileType(filename)
    :members: pprint, add_tags, mime
    :show-inheritance:

    .. automethod:: delete()

    .. automethod:: save()


.. autoclass:: mutagen.Tags

    .. automethod:: pprint()


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


Other Classes
~~~~~~~~~~~~~

.. class:: text()

    This type only exists for documentation purposes. It represents
    :obj:`unicode` under Python 2 and :obj:`str` under Python 3.


.. class:: bytes()

    This type only exists for documentation purposes. It represents
    :obj:`python:str` under Python 2 and :obj:`python3:bytes` under Python 3.

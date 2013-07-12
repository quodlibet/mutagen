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


.. autoclass:: mutagen.Metadata

    .. automethod:: delete()

    .. automethod:: save()


Internal Classes
~~~~~~~~~~~~~~~~

.. automodule:: mutagen._util

.. autoclass:: mutagen._util.DictMixin

.. autoclass:: mutagen._util.DictProxy
    :show-inheritance:

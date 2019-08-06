"""JSON serializer"""
from os import fsdecode as _fsdecode
from os.path import realpath as _realpath

from json import (dump as _json_dump, load as _json_load,
                  JSONDecodeError as _JSONDecodeError)

from accelpy.exceptions import ConfigurationException as _ConfigurationException


def json_read(path, **kwargs):
    """
    Read a JSON file.

    Args:
        path (path-like object): Path to file to load.
        kwargs: "json.load" kwargs.

    Returns:
        dict or list: Un-serialized content
    """
    path = _realpath(_fsdecode(path))
    with open(path, 'rt') as file:
        try:
            return _json_load(file, **kwargs)

        except _JSONDecodeError as exception:
            raise _ConfigurationException(
                f'Unable to read "{path}": {str(exception)}')


def json_write(data, path, **kwargs):
    """
    Write a JSON file

    Args:
        data (dict or list): data to serialize.
        path (path-like object): Path where save file.
        kwargs: "json.dump" kwargs.
    """
    with open(_fsdecode(path), 'wt') as file:
        _json_dump(data, file, **kwargs)
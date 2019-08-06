"""YAML serializer"""
from os import fsdecode as _fsdecode
from os.path import realpath as _realpath

try:
    # Use LibYAML if available
    from yaml import CSafeLoader as _Loader, CDumper as _Dumper
except ImportError:
    # Else use pure-Python library
    from yaml import SafeLoader as _Loader, Dumper as _Dumper

from yaml import dump as _yaml_dump, load as _yaml_load, YAMLError as _YAMLError

from accelpy.exceptions import ConfigurationException as _ConfigurationException


def yaml_read(path):
    """
    Read a YAML file.

    Args:
        path (path-like object): Path to file to load.

    Returns:
        dict or list: Un-serialized content
    """
    path = _realpath(_fsdecode(path))
    with open(path, 'rt') as file:
        try:
            return _yaml_load(file, Loader=_Loader)

        except _YAMLError as exception:
            raise _ConfigurationException(
                f'Unable to read "{path}": {str(exception)}')


def yaml_write(data, path, **kwargs):
    """
    Write a YAML file

    Args:
        data (dict or list): data to serialize.
        path (path-like object): Path where save file.
        kwargs: "yaml.dump" kwargs.
    """
    with open(_fsdecode(path), 'wt') as file:
        _yaml_dump(data, file, Dumper=_Dumper, **kwargs)
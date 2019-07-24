# coding=utf-8
"""Global configuration"""
from importlib import import_module as _import_module
from json import dump as _json_dump, load as _json_load
from json.decoder import JSONDecodeError as _JSONDecodeError
from os import (fsdecode as _fsdecode, symlink as _symlink, chmod as _chmod,
                makedirs as _makesdirs, scandir as _scandir,
                environ as _environ)
from os.path import (
    expanduser as _expanduser, isdir as _isdir, realpath as _realpath,
    join as _join, dirname as _dirname, basename as _basename,
    isfile as _isfile, splitext as _splitext)
from collections.abc import Mapping as _Mapping
from subprocess import run as _run, PIPE as _PIPE

try:
    # Use LibYAML if available
    from yaml import CSafeLoader as _Loader, CDumper as _Dumper
except ImportError:
    # Else use pure-Python library
    from yaml import SafeLoader as _Loader, Dumper as _Dumper
from yaml import dump as _yaml_dump, load as _yaml_load, YAMLError as _YAMLError

from accelpy.exceptions import (
    RuntimeException as _RuntimeException,
    ConfigurationException as _ConfigurationException)

#: User configuration directory
HOME_DIR = _expanduser('~/.accelize')

# Ensure directory exists and have restricted access rights
_makesdirs(HOME_DIR, exist_ok=True)
_chmod(HOME_DIR, 0o700)


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


def recursive_update(to_update, update):
    """
    Recursively updates nested directories.

    Args:
        to_update (dict or collections.Mapping):
            dict to update.
        update (dict or collections.Mapping):
            dict containing new values.

    Returns:
        dict: to_update
    """
    if update:
        for key, value in update.items():
            if isinstance(value, _Mapping):
                value = recursive_update(to_update.get(key, {}), value)
            to_update[key] = value
    return to_update


def call(command, check=True, pipe_stdout=False, **run_kwargs):
    """
    Call command in subprocess.

    Args:
        command (iterable of str): Command
        run_kwargs: subprocess.run keyword arguments.
        check (bool): If True, Check return code for error.
        pipe_stdout (bool): If True, redirect stdout into a pipe, this allow to
            hide outputs from sys.stdout and permit to retrieve stdout as
            "result.stdout".

    Returns:
        subprocess.CompletedProcess: Utility call result.
    """
    if pipe_stdout:
        run_kwargs.setdefault('stdout', _PIPE)

    result = _run(command, universal_newlines=True, stderr=_PIPE, **run_kwargs)

    if check and result.returncode:
        raise _RuntimeException((result.stderr or result.stdout or
                                'See stdout for more information.').strip())

    return result


def get_sources_dirs(*src):
    """
    Return sources directories.

    Args:
        *src: Directories paths.

    Returns:
        list of str: Sources directories
    """
    paths = [HOME_DIR, '.']
    paths.extend(src)
    return [_realpath(_fsdecode(path)) for path in paths if path]


def symlink(src, dst):
    """
    Extended "os.symlink" that:
    - Autodetect if target is directory.
    - Ignore error if file already exists.
    - Ensure to link to real absolute path of the source.

    Args:
        src (path-like object): Source path.
        dst (path-like object): Destination path.
    """
    src = _realpath(_fsdecode(src))
    try:
        _symlink(src, _fsdecode(dst), target_is_directory=_isdir(src))
    except FileExistsError:
        pass


def get_sources_filters(provider, application):
    """
    Return names to use to filer sources

    Args:
        provider (str): provider name.
        application (str): Application type.

    Returns:
        list of str: sources names
    """
    return [key for key in
            ('common', provider.split(',')[0], application) if key]


def get_python_package_entry_point(package, entry_point):
    """
    Find an CLI entry point from a Python package.

    Args:
        package (str): Package name.
        entry_point (str): Entry point name.

    Returns:
        str or None: Path to entry point, or None if nothing found.
    """
    site_packages_path = _dirname(_import_module(package).__path__[0])

    # Find package info
    # Can be a directory ending by ".dist-info" or ".egg-info"
    with _scandir(site_packages_path) as entries:
        for entry in entries:
            if (entry.name.startswith(f'{package}-') and
                    _splitext(entry.name)[1] in ('.dist-info', '.egg-info')):
                package_info_path = entry.path
                break

        else:
            # Package is not installed or do not have package info
            return None

    # Find manifest file
    # Can be a "RECORD" or a "installed-files.txt" file in package info folder
    for name in ('RECORD', 'installed-files.txt'):
        manifest_path = _join(package_info_path, name)
        if _isfile(manifest_path):
            break

    else:
        # Package do not have manifest file
        return None

    # Find entry point relative path in manifest file
    # Possibles manifest file lines formats: "path\n" or "path,checksum\n"
    with open(manifest_path, 'rt') as manifest:

        for line in manifest:
            entry_point_rel_path = line.strip().split(',', 1)[0]
            if _basename(entry_point_rel_path) == entry_point:
                break

        else:
            # Entry point is not present in manifest
            return None

    # Convert to absolute path
    # Paths in manifest are relative to site-packages or package info
    for prefix in (site_packages_path, package_info_path):
        entry_point_path = _realpath(_join(prefix, entry_point_rel_path))

        if _isfile(entry_point_path):
            return entry_point_path


def no_color():
    """
    If "ACCELPY_NO_COLOR" environment variable is set, return True.

    Returns:
        bool: True if no color mode.
    """
    return bool(_environ.get("ACCELPY_NO_COLOR", False))


def debug():
    """
    If "ACCELPY_DEBUG" environment variable is set, return True.

    Returns:
        bool: True if debug mode.
    """
    return bool(_environ.get("ACCELPY_DEBUG", False))

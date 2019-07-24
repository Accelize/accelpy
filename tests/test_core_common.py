# coding=utf-8
"""Common functions tests"""
import pytest


def test_recursive_update():
    """Tests test_recursive_update"""
    from accelpy._common import recursive_update

    to_update = {'root1': {'key1': 1, 'key2': 2}, 'key3': 3}
    update = {'root1': {'key1': 1.0, 'key4': 4.0}, 'key5': 5.0, 'key6': {}}
    expected = {'root1': {'key1': 1.0, 'key2': 2, 'key4': 4.0},
                'key3': 3, 'key5': 5.0, 'key6': {}}

    assert recursive_update(to_update, update) == expected


def test_json_read_write(tmpdir):
    """
    Test json_read/json_write

    Args:
        tmpdir (py.path.local) tmpdir pytest fixture
    """
    from accelpy._common import json_read, json_write
    from accelpy.exceptions import ConfigurationException

    json_file = tmpdir.join('file.json')

    # Test: correct file
    data = {'key': 'value'}
    json_write(data, json_file)
    assert json_read(json_file) == data

    # Test: badly formatted file
    json_file.write('{key: ')
    with pytest.raises(ConfigurationException):
        json_read(json_file)


def test_yaml_read_write(tmpdir):
    """
    Test yaml_read/yaml_write

    Args:
        tmpdir (py.path.local) tmpdir pytest fixture
    """
    from accelpy._common import yaml_read, yaml_write
    from accelpy.exceptions import ConfigurationException

    yam_file = tmpdir.join('file.yml')

    # Test: correct file
    data = {'key': 'value'}
    yaml_write(data, yam_file)
    assert yaml_read(yam_file) == data

    # Test: badly formatted file
    yam_file.write('key: "')
    with pytest.raises(ConfigurationException):
        yaml_read(yam_file)


def test_get_python_package_entry_point(tmpdir):
    """
    Test get_python_package_entry_point

    Args:
        tmpdir (py.path.local) tmpdir pytest fixture
    """
    import accelpy._common as common
    from accelpy._common import get_python_package_entry_point

    # Mock importlib

    site_packages = tmpdir.ensure('sites-package', dir=True)

    class ImportModule:
        """Mocked module"""

        def __init__(self, module):
            self.__path__ = [str(site_packages.ensure(module, dir=True))]

    common_import_module = common._import_module
    common._import_module = ImportModule

    # Run tests
    try:
        package_name = 'module'
        dist_info = f'{package_name}-1.0.0.dist-info'
        egg_info = f'{package_name}-1.0.0.egg-info'
        entry_point_name = 'entry_point'
        entry_point_path = tmpdir.ensure(entry_point_name)
        args = (package_name, entry_point_name)

        # No package info
        assert get_python_package_entry_point(*args) is None

        # Empty dist-info
        site_packages.ensure(dist_info, dir=True)
        assert get_python_package_entry_point(*args) is None

        # Entry point not found in dist-info
        site_packages.join(dist_info).join('RECORD').write_text(
            'module/module.py,sdjdfjgdjlfkglkf\n', encoding='utf-8')
        assert get_python_package_entry_point(*args) is None

        # Entry point found in dist-info
        site_packages.join(dist_info).join('RECORD').write_text(
            f'{package_name}/module.py,sdjdfjgdjlfkglkf\n'
            f'../{entry_point_name},dfgdfgsdfgdsfgsd\n', encoding='utf-8')
        assert get_python_package_entry_point(*args) == str(entry_point_path)

        # Entry point found in egg-info
        site_packages.join(dist_info).remove(rec=1)
        site_packages.ensure(egg_info, dir=True)
        site_packages.join(egg_info).join('installed-files.txt').write_text(
            f'../{package_name}/module.py\n'
            f'../../{entry_point_name}\n', encoding='utf-8')
        assert get_python_package_entry_point(*args) == str(entry_point_path)

        # Entry point file not exists
        entry_point_path.remove()
        assert get_python_package_entry_point(*args) is None

    finally:
        common._import_module = common_import_module

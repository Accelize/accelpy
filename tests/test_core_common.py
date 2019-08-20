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
    from accelpy._common import json_write, json_read
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
    from accelpy._yaml import yaml_write, yaml_read
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


def test_cli_cache(tmpdir):
    """
    Test CLI cache.

    Args:
        tmpdir (py.path.local) tmpdir pytest fixture
    """
    from time import time
    from os import environ
    import accelpy._common as common
    from accelpy._common import get_cli_cache, set_cli_cache

    # Mock cache
    environ['ACCELPY_CLI'] = 'True'
    common_cache_dir = common.CACHE_DIR
    common.CACHE_DIR = str(tmpdir.join('cache').ensure(dir=True))

    # Tests
    try:
        value = [0, 1, 2, 3]

        # Test set cache
        set_cli_cache('test1', value)

        # Test get from cache
        assert get_cli_cache('test1') == value

        # Test get from cache recursively
        assert get_cli_cache('test1', recursive=True) == value
        assert get_cli_cache('test12', recursive=True) == value

        # Test expiry from timestamp (Ensure always expired)
        set_cli_cache('test2', value, expiry_timestamp=int(time()) - 1)
        assert get_cli_cache('test2') is None

        # Test expiry from seconds (Ensure always expired)
        set_cli_cache('test3', value, expiry_seconds=-1)
        assert get_cli_cache('test3') is None

        # Test cache previously expired
        assert get_cli_cache('test3') is None

    # Clean up
    finally:
        common.CACHE_DIR = common_cache_dir
        del environ['ACCELPY_CLI']


def test_accelize_ws_session(tmpdir):
    """
    Test Accelize Web Service session

    Args:
        tmpdir (py.path.local) tmpdir pytest fixture
    """
    from io import BytesIO
    from os import environ
    from json import dumps
    from time import time
    from requests import Response, Session
    import accelpy._common as common
    from accelpy._common import _AccelizeWSSession, json_write
    from accelpy.exceptions import AuthenticationException, WebServerException

    # Mock cache
    environ['ACCELPY_CLI'] = 'True'
    common_cache_dir = common.CACHE_DIR
    common.CACHE_DIR = str(tmpdir.join('cache_01').ensure(dir=True))

    # Mock get_accelize_cred
    cred_json = str(tmpdir.join('cred.json'))
    json_write(dict(client_id='accelpy_testing', client_secret=''), cred_json)
    common_get_accelize_cred = common.get_accelize_cred

    def get_accelize_cred():
        """
        Returns bad credentials.

        Returns:
            str: path
        """
        return cred_json

    common.get_accelize_cred = get_accelize_cred

    # Test Session initialization
    session = _AccelizeWSSession()
    assert session._request

    # Mock server response
    resp_status_code = 200
    resp_content = dict(key='value')
    auth_status_code = 200
    auth_expire_in = 9999

    class _Session(Session):
        """Mocked requests.Session"""
        raw_error = False

        @classmethod
        def request(cls, method, url, **_):
            """Returns mocked response"""
            if '/o/token/' in url:
                status_code = auth_status_code
                content = dumps(dict(
                    access_token='access_token', expires_in=auth_expire_in))
            else:
                status_code = resp_status_code
                content = dumps(resp_content) if resp_content else ''

            if status_code != 200:
                if cls.raw_error:
                    content = dumps(dict(detail='error'))
                else:
                    # Test return a non JSON error once
                    cls.raw_error |= True
                    content = 'error'

            response = Response()
            response.raw = BytesIO(content.encode())
            response.raw.seek(0)
            response.status_code = status_code
            return response

    session._session = _Session()
    session._session_request = session._session.request

    # Tests
    try:
        # Test: invalid credentials
        auth_status_code = 400
        with pytest.raises(AuthenticationException):
            session.request(path='')

        # Test: get token from web service
        auth_status_code = 200
        session._token = ''
        assert session.request(path='') == resp_content

        # Test: get token from cache
        auth_status_code = 500
        session._token = ''
        assert session.request(path='') == resp_content

        # Test: use existing token
        assert session.request(path='') == resp_content

        # Test: renew token from web service if expired
        common.CACHE_DIR = str(tmpdir.join('cache_02').ensure(dir=True))
        session._token_expire = int(time()) - 10
        with pytest.raises(AuthenticationException):
            session.request(path='')

        auth_status_code = 200
        assert session.request(path='') == resp_content

        # Test: Renew token if server reject it
        resp_status_code = 401
        with pytest.raises(WebServerException):
            session.request(path='')
        assert session._token

        # Test: Empty response
        resp_content = ''
        resp_status_code = 200
        assert session.request(path='') is None

    # Restore mocked function
    finally:
        common.get_accelize_cred = common_get_accelize_cred
        common.CACHE_DIR = common_cache_dir
        del environ['ACCELPY_CLI']


def test_color_str():
    """
    Test color_str
    """
    import accelpy._common as common
    from accelpy._common import color_str

    # Mock environment functions
    is_cli = False

    def _is_cli():
        """Simulate CLI use"""
        return is_cli

    def no_color():
        """Ensure color is enabled"""
        return False

    common_is_cli = common.is_cli
    common_no_color = common.no_color
    common.is_cli = _is_cli
    common.no_color = no_color

    # Tests
    try:
        # Test: CLI disabled
        assert color_str('test', 'RED') == 'test'

        # Test: ClI enabled
        is_cli = True
        assert color_str('test', 'RED') == '\033[31mtest\033[30m'

    # Restore mocked functions
    finally:
        common.is_cli = common_is_cli
        common.no_color = common_no_color


def test_call():
    """
    Test call
    """
    from subprocess import CompletedProcess, PIPE
    import accelpy._common as common
    from accelpy.exceptions import RuntimeException
    from accelpy._common import call

    # Mock subprocess
    retries = {}
    returncode = 0

    def run(*args, **kwargs):
        """Mocker run"""
        if retries:
            # Simulate failure to retry
            result = CompletedProcess(args, 1)
            retries.clear()

        else:
            result = CompletedProcess(args, returncode)

        result.kwargs = kwargs
        return result

    common_run = common._run
    common._run = run

    # Tests
    try:

        # Test: pipe_stdout
        assert 'stdout' not in call([]).kwargs
        assert call([], pipe_stdout=True).kwargs['stdout'] == PIPE

        # Test: Passing keyword arguments
        assert call([], testing=True).kwargs['testing'] is True

        # Test: retries
        retries[0] = 0
        assert call([], retries=3).returncode == returncode
        assert not retries

        # Test: check
        returncode = 1
        assert call([], check=False).returncode == returncode
        with pytest.raises(RuntimeException):
            call([], check=True)

    # Restore mocked functions
    finally:
        common._run = common_run

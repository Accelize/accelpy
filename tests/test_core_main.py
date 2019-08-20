# coding=utf-8
"""Command line interface tests"""


def generate_name():
    """
    Generate test host name.

    Returns:
        str: name
    """
    from uuid import uuid1
    return f'pytest_{str(uuid1())}'


def cli(*args, **env):
    """
    Call cli

    Args:
        *args: CLI arguments.
        **env: Environment variables

    Returns:
        subprocess.CompletedProcess: Utility call result.
    """
    from os import environ
    from sys import executable
    from accelpy._common import call
    from accelpy.__main__ import __file__ as cli_exec

    call_env = environ.copy()
    call_env.update(env)

    return call([executable, cli_exec] + [str(arg) for arg in args],
                pipe_stdout=True, check=False, env=call_env)


def test_command_line_interface(tmpdir):
    """
    Tests the command line interface.

    Args:
        tmpdir (py.path.local) tmpdir pytest fixture
    """

    import accelpy._host as accelpy_host

    from py.path import local  # Use same path interface as Pytest

    from tests.test_core_terraform import mock_terraform_provider
    from tests.test_core_packer import mock_packer_provider
    from tests.test_core_ansible import mock_ansible_local
    from tests.test_core_application import mock_application

    source_dir = tmpdir.join('source').ensure(dir=True)

    # Get user config dir
    config_dir = local(accelpy_host.CONFIG_DIR)
    name = generate_name()
    host_config_dir = config_dir.join(name)
    latest = config_dir.join('latest')

    # Mock application definition file & provider specific configuration
    application = mock_application(source_dir)
    mock_terraform_provider(source_dir)
    artifact = mock_packer_provider(source_dir)
    source_dir.ensure('cred.json')

    # Function to call the CLI

    try:
        # Test: no action should raise
        result = cli()
        assert result.returncode

        # Test: lint application file
        result = cli('lint', application)
        assert not result.returncode

        # Test: Lint with not file should raise
        result = cli('lint')
        assert result.returncode

        # Test: Lint with not existing file should raise
        result = cli('lint', source_dir.join('no_exists.yml'))
        assert result.returncode

        # Test: Not initialized should raise
        if latest.isfile():
            latest.remove()
        result = cli('plan')
        assert result.returncode

        # Test: init
        result = cli('init', '-n', name, '-a', application, '-c', source_dir,
                     '-p', 'testing')
        assert not result.returncode

        # Test: Bad name should raise
        result = cli('plan', '-n', 'pytest_not_exists', ACCELPY_DEBUG='')
        assert result.returncode

        # Test: Debug mode should still raise
        result = cli('plan', '-n', 'pytest_not_exists', ACCELPY_DEBUG='True')
        assert result.returncode

        # Test: plan
        result = cli('plan', '-n', name)
        assert not result.returncode
        assert result.stdout

        # Mock ansible playbook
        mock_ansible_local(host_config_dir)

        # Test: apply
        result = cli('apply', '-n', name, '-q')
        assert not result.returncode

        # Test: apply not quiet
        result = cli('apply', '-n', name)
        assert not result.returncode

        # Test: build
        result = cli('build', '-n', name, '-q')
        assert not result.returncode
        assert result.stdout.strip() == artifact

        # Test: ssh_private_key
        result = cli('ssh_private_key', '-n', name)
        assert not result.returncode
        assert str(host_config_dir) in result.stdout

        # Test: Not specifying name should use last called name
        result = cli('ssh_private_key')
        assert not result.returncode
        assert str(host_config_dir) in result.stdout

        # Test: private_ip
        result = cli('private_ip', '-n', name)
        assert not result.returncode
        assert result.stdout.strip() == '127.0.0.1'

        # Test: public_ip
        result = cli('public_ip', '-n', name)
        assert not result.returncode
        assert result.stdout.strip() == '127.0.0.1'

        # Test: ssh_user
        result = cli('ssh_user', '-n', name)
        assert not result.returncode
        assert result.stdout.strip() == 'user'

        # Test: list
        result = cli('list')
        assert not result.returncode
        assert name in result.stdout

        # Test: push (Only test call, push function tested in another test)
        result = cli('push', application)
        assert result.returncode

        # Test: destroy
        result = cli('destroy', '-n', name, '-d', '-q')
        assert not result.returncode
        assert not host_config_dir.isdir()

        # Test: Loading destroyed should raise
        result = cli('plan')
        assert result.returncode

        # Test: name generation
        result = cli(
            'init', '-a', application, '-c', source_dir, '-p', 'testing')
        assert not result.returncode
        name = result.stdout.strip()
        assert name
        assert not cli('destroy', '-d', '-q').returncode

    # Clean up
    finally:
        if host_config_dir.isdir():
            host_config_dir.remove(rec=1, ignore_errors=True)
        if config_dir.join(name).isdir():
            config_dir.join(name).remove(rec=1, ignore_errors=True)
        if latest.isfile():
            latest.remove(ignore_errors=True)


def test_command_line_autocomplete(tmpdir):
    """
    Tests the command line autocompletion.

    Args:
        tmpdir (py.path.local) tmpdir pytest fixture
    """
    from argparse import Namespace
    from os import environ, chdir, getcwd
    from os.path import relpath, isdir, join, dirname
    import accelpy._common as common
    from accelpy.exceptions import AuthenticationException
    import accelpy._application as accelpy_app
    from accelpy.__main__ import (
        _completer_warn, _application_completer, _provider_completer,
        _yaml_completer)

    # Mock cache
    cwd = getcwd()
    environ['ACCELPY_CLI'] = 'True'
    common_cache_dir = common.CACHE_DIR
    common.CACHE_DIR = str(tmpdir.join('cache').ensure(dir=True))

    # Mock Application
    server_apps = ['accelize.com/accelpy/test', 'accelize.com/accelpy/ci']
    server_versions = ['1.0.0', '1.1.1', '2.0.0']
    server_raises = False

    class Application(accelpy_app.Application):
        """Mocked Application"""

        @staticmethod
        def list(prefix=''):
            """
            List applications

            Args:
                prefix (str): prefix

            Returns:
                list of str: applications
            """
            if server_raises:
                raise AuthenticationException('Error')
            return [value for value in server_apps if value.startswith(prefix)]

        @staticmethod
        def list_versions(product_id, prefix=''):
            """
            List versions.

            Args:
                product_id (str): product_id
                prefix (str): prefix

            Returns:
                list of str: version
            """
            return [value for value in server_versions if
                    value.startswith(prefix)]

    accelpy_application_application = accelpy_app.Application
    accelpy_app.Application = Application

    # Tests
    try:

        # Should not raises
        _completer_warn('Warning message')

        # Test yaml completer with absolute paths
        matching = []
        not_matching = []
        yaml_dir = tmpdir.join('yaml')
        sub_yaml_dir = yaml_dir.join('matching_dir').ensure(dir=True)
        matching.append(sub_yaml_dir)
        matching.append(yaml_dir.join('matching.yml').ensure())
        matching.append(yaml_dir.join('matching.yaml').ensure())
        not_matching.append(yaml_dir.join('not_matching.yml').ensure())
        not_matching.append(yaml_dir.join('matching.not_yml').ensure())

        matching = [str(path) for path in matching]
        matching = [path + '/' if isdir(path) else path for path in matching]
        not_matching = [str(path) for path in not_matching]

        prefix = str(yaml_dir.join('matching'))
        result = list(_yaml_completer(prefix, Namespace()))

        for path in matching:
            assert path in result, path
        for path in not_matching:
            assert path not in result, path

        # Test yaml completer with relative path thought _application_completer
        chdir(str(yaml_dir))

        matching = [relpath(path) for path in matching]
        matching = [path + '/' if isdir(path) else path for path in matching]
        not_matching = [relpath(path) for path in not_matching]

        prefix = './matching'
        result = list(_application_completer(prefix, Namespace()))

        for path in matching:
            assert path in result, path
        for path in not_matching:
            assert path not in result, path

        # Test yaml completer with bad path
        assert not list(_yaml_completer(
            str(yaml_dir.join('not_exits/not_exists')), Namespace()))

        # Test Application completer from server
        assert list(_application_completer(
            'accelize.com', Namespace())) == server_apps
        assert list(_application_completer(
            'accelize.com/accelpy/test:', Namespace())) == [
            f'accelize.com/accelpy/test:{version}'
            for version in server_versions]

        # Test Application completer from cache
        assert list(_application_completer(
            'accelize.com/accelpy/t', Namespace())) == [
            'accelize.com/accelpy/test']
        assert list(_application_completer(
            'accelize.com/accelpy/test:2.', Namespace())) == [
            'accelize.com/accelpy/test:2.0.0']

        # Test application warning
        server_raises = True
        assert _application_completer('', Namespace()) is None

        # Test Provider completer, not application
        assert not _provider_completer('error', Namespace(application=None))

        # test Provider completer from definition
        excepted = ["aws,eu-west-1,f1"]
        app_yaml = join(dirname(__file__), 'test_app_container_service.yml')
        assert list(_provider_completer(
            '', Namespace(application=app_yaml))) == excepted

        assert not list(_provider_completer(
            'no_exists', Namespace(application=app_yaml)))

        # test Provider completer from cache
        assert list(_provider_completer(
            '', Namespace(application=app_yaml))) == excepted

    # Clean up
    finally:
        accelpy_app.Application = accelpy_application_application
        common.CACHE_DIR = common_cache_dir
        chdir(cwd)
        del environ['ACCELPY_CLI']

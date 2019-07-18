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


def cli(*args):
    """
    Call cli

    Args:
        *args: CLI arguments.

    Returns:
        subprocess.CompletedProcess: Utility call result.
    """
    from sys import executable
    from accelpy._common import call
    from accelpy.__main__ import __file__ as cli_exec

    return call([executable, cli_exec] + [str(arg) for arg in args],
                pipe_stdout=True, check=False)


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
        result = cli('plan', '-n', 'pytest_not_exists')
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

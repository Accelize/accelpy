"""Test application"""
import pytest


def get_name(app):
    """
    Get a unique name for test generated host.

    args:
        application (accelpy._application.Application): application:

    returns:
        str: name
    """
    from uuid import uuid4 as uuid
    return (f'accelpy_{app["application"]["product_id"]}'
            f'_{str(uuid()).replace("-", "")[:8]}')


@pytest.mark.molecule
def test_ansible_role(ansible_role):
    """
    Test roles using molecule.

    Args:
        ansible_role (str): Path to role.
    """
    from subprocess import run, STDOUT

    if run(['molecule', 'test'], stderr=STDOUT, cwd=ansible_role).returncode:
        pytest.fail(pytrace=False)


@pytest.mark.require_csp
def test_application(application_yml, tmpdir):
    """
    Test applications based on their application definition.

    Args:
        application_yml (dict): Application detail.
        tmpdir (py.path.local) tmpdir pytest fixture.
    """
    from os import environ
    from time import sleep
    from subprocess import run, STDOUT, PIPE
    import accelpy._host as accelpy_host
    from accelpy._host import Host
    from accelpy._application import Application

    yaml_path = application_yml['path']
    provider = application_yml['provider']

    environ['ACCELPY_DEBUG'] = 'True'

    # Mock config dir
    accelpy_host_config_dir = accelpy_host.CONFIG_DIR
    config_dir = tmpdir.join('config').ensure(dir=True)
    accelpy_host.CONFIG_DIR = str(config_dir)

    app = Application(yaml_path)

    # Tests
    try:

        with Host(application=yaml_path, provider=provider,
                  name=get_name(app), destroy_on_exit=True,
                  keep_config=False) as host:

            # Run Packer configuration check
            host._packer.validate()

            # Apply configuration
            host.apply()

            # Get test command
            command = app[provider]['test']['shell']
            if not command:
                pytest.xfail('No test defined')

            # Run test
            else:
                # Evaluate "accelpy" shell variables
                for attr in dir(host):

                    if attr.startswith('_'):
                        continue

                    shell_var = f'$(accelpy {attr})'
                    if shell_var in command:
                        command = command.replace(
                            shell_var, getattr(host, attr))

                # Run test command
                sleep(5)

                print(f'\nRunning test command:\n{command.strip()}\n')
                result = run(command, universal_newlines=True,
                             stderr=STDOUT, stdout=PIPE, shell=True)
                print(f'\nTest command returned: '
                      f'{result.returncode}\n{result.stdout}')

                if result.returncode:
                    pytest.fail(pytrace=False)

    # Restore mocked config dir
    finally:
        accelpy_host.CONFIG_DIR = accelpy_host_config_dir
        del environ['ACCELPY_DEBUG']


@pytest.mark.require_csp
def test_host_mocked(tmpdir):
    """
    Test existing host provisioning on a mocked host.

    Args:
        tmpdir (py.path.local) tmpdir pytest fixture
    """
    from os import environ
    from os.path import dirname, join
    import accelpy._host as accelpy_host
    from accelpy._host import Host
    from accelpy._application import Application

    environ['ACCELPY_DEBUG'] = 'True'

    mocked_app_path = join(dirname(__file__), 'host_mock.yml')
    app = join(dirname(__file__), 'host_app.yml')

    # Mock config dir
    accelpy_host_config_dir = accelpy_host.CONFIG_DIR
    config_dir = tmpdir.join('config').ensure(dir=True)
    accelpy_host.CONFIG_DIR = str(config_dir)

    # Mock user_config dir
    user_config = tmpdir.join('user_config').ensure(dir=True)

    # Mock an existing host with a virtual machine
    mocked_app = Application(mocked_app_path)
    mocked_provider = mocked_app.providers.pop()
    mocked_host = Host(name=get_name(mocked_app), application=mocked_app_path,
                       provider=mocked_provider)

    try:
        # Create host
        mocked_host.apply(quiet=True)

        # Create the existing host Terraform configuration override
        user_config.join('host.user_override.tf').write_text('\n'.join((
            'locals {',
            f'  host_ip          = ["{mocked_host.public_ip}"]',
            f'  ssh_key_pem      = "{mocked_host.ssh_private_key}"',
            f'  remote_user      = "{mocked_host.ssh_user}"',
            f'  require_ask_pass = false',
            '}')), encoding='utf-8')

        # Provision existing host
        with Host(application=app, user_config=user_config,
                  provider=f'host,{mocked_provider.replace(",", "-")}',
                  destroy_on_exit=True, keep_config=False) as host:
            host.apply()

    # Restore mocked configuration
    finally:
        try:
            mocked_host.destroy(quiet=True, delete=True)
        finally:
            accelpy_host.CONFIG_DIR = accelpy_host_config_dir
            del environ['ACCELPY_DEBUG']

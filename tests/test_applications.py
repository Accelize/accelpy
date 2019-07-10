"""Test application"""
import pytest


def test_ansible_roles(ansible_role):
    """
    Test roles using molecule.

    Args:
        ansible_role (str): Path to role.
    """
    from subprocess import run, STDOUT

    if run(['molecule', 'test'], stderr=STDOUT, cwd=ansible_role).returncode:
        pytest.fail(pytrace=False)


@pytest.mark.require_csp
def test_apply(application_yml, tmpdir):
    """
    Test applications based on their application definition.

    Args:
        application_yml (dict): Application detail.
        tmpdir (py.path.local) tmpdir pytest fixture
    """
    from time import sleep
    from subprocess import run, STDOUT, PIPE
    import accelpy._host as accelpy_host
    from accelpy._host import Host
    from accelpy._application import Application

    yaml_path = application_yml['path']
    provider = application_yml['provider']

    # Mock config dir
    accelpy_host_config_dir = accelpy_host.CONFIG_DIR
    config_dir = tmpdir.join('config').ensure(dir=True)
    accelpy_host.CONFIG_DIR = str(config_dir)

    # Tests
    try:

        with Host(application=yaml_path, provider=provider,
                  destroy_on_exit=True, keep_config=False) as host:

            # Apply configuration
            host.apply()

            # Get test command
            command = Application(yaml_path).get(
                'test', 'shell', env=provider)

            # Evaluate "accelpy" shell variables
            for attr in dir(host):

                if attr.startswith('_'):
                    continue

                shell_var = f'$(accelpy {attr})'
                if shell_var in command:
                    command = command.replace(shell_var, getattr(host, attr))

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

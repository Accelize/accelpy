# coding=utf-8
"""Ansible handler tests"""
import pytest


def mock_ansible_local(config_dir):
    """
    Mock Ansible playbook to performs local do-nothing execution.

    Args:
        config_dir (py.path.local) Configuration directory.
    """
    from accelpy._yaml import yaml_write
    yaml_write([{
        "hosts": "127.0.0.1",
        "connection": "local"
    }], config_dir.join('playbook.yml'))


def ansible_lint(role, **kwargs):
    """
    Lint Ansible role.

    Args:
        role (str): Path to role 
    """
    from accelpy._ansible import Ansible

    # Run Ansible lint
    return Ansible(role)._ansible(
        '-x701,702,703,704',  # Skip Ansible galaxy related rules
        '.', utility='lint', **kwargs)


def yaml_lint(files, **kwargs):
    """
    Lint YAML files.

    Args:
        files (list of str): Paths to YAML files.
    """
    from accelpy._common import call
    return call(['yamllint', '-s'] + files, **kwargs)


def test_ansible(tmpdir):
    """
    Test Ansible handler

    Args:
        tmpdir (py.path.local) tmpdir pytest fixture
    """
    from accelpy._ansible import Ansible
    from accelpy._yaml import yaml_read

    source_dir = tmpdir.join('source').ensure(dir=True)
    config_dir = tmpdir.join('config').ensure(dir=True)
    role_dir = tmpdir.join('roles').ensure(dir=True)
    variables = dict(key='value')

    # Test: Create configuration (With not specific provider and application)
    ansible = Ansible(config_dir)
    ansible.create_configuration(variables=variables, user_config=source_dir)
    playbook = yaml_read(config_dir.join('playbook.yml'))[0]
    assert 'pre_tasks' in playbook
    assert playbook['vars'] == variables
    assert 'common.init' in playbook['roles']

    # Test: Re-create should not raise
    ansible.create_configuration()

    # Test: Galaxy install role
    role_dir.join('accelize.accelize_drm').ensure(dir=True)  # Mock existing
    ansible.galaxy_install(
        ['accelize.accelize_drm', 'accelize.aws_fpga'], str(role_dir))

    # Test: Galaxy install should do nothing if no roles
    ansible.galaxy_install([], str(role_dir))

    # Test: Create configuration (with application that requires dependencies)
    ansible = Ansible(config_dir)
    ansible.create_configuration(application_type='container_service')
    playbook = yaml_read(config_dir.join('playbook.yml'))[0]
    assert 'pre_tasks' in playbook
    assert not playbook['vars']
    assert 'container_service' in playbook['roles']


def test_ansible_lint():
    """
    Lint Ansible roles with "ansible-lint" and "yamllint".
    """
    from concurrent.futures import ThreadPoolExecutor
    from os import scandir, walk
    from os.path import dirname, join, splitext
    from accelpy._ansible import __file__ as ansible_py_file

    futures = []
    success = True
    roles = []
    with scandir(join(dirname(ansible_py_file), 'roles')) as entries:
        for entry in entries:
            if entry.is_dir():
                roles.append(entry.path)

    with ThreadPoolExecutor() as executor:
        for role in roles:
            futures.append(executor.submit(
                ansible_lint, role, pipe_stdout=True, check=False))

            yml_files = []
            for root, _, files in walk(role):
                for name in files:
                    if splitext(name)[1].lower() in ('.yml', '.yaml'):
                        yml_files.append(join(root, name))

            futures.append(executor.submit(
                yaml_lint, yml_files, pipe_stdout=True, check=False))

    for future in futures:
        result = future.result()
        if result.returncode:
            success = False
        if result.stdout:
            print(result.stdout)

    if not success:
        pytest.fail(pytrace=False)

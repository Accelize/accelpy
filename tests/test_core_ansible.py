# coding=utf-8
"""Ansible handler tests"""


def mock_ansible_local(config_dir):
    """
    Mock Ansible playbook to performs local do-nothing execution.

    Args:
        config_dir (py.path.local) Configuration directory.
    """
    from accelpy._common import yaml_write
    yaml_write([{
        "hosts": "127.0.0.1",
        "connection": "local"
    }], config_dir.join('playbook.yml'))


def test_ansible(tmpdir):
    """
    Test Ansible handler

    Args:
        tmpdir (py.path.local) tmpdir pytest fixture
    """
    from accelpy._ansible import Ansible
    from accelpy._common import yaml_read

    source_dir = tmpdir.join('source').ensure(dir=True)
    config_dir = tmpdir.join('config').ensure(dir=True)
    role_dir = tmpdir.join('roles').ensure(dir=True)
    variables = dict(key='value')

    # Test: Create configuration (With not specific provider and application)
    ansible = Ansible(config_dir, variables=variables, user_config=source_dir)
    ansible.create_configuration()
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
    ansible = Ansible(config_dir, application_type='container_service')
    ansible.create_configuration()
    playbook = yaml_read(config_dir.join('playbook.yml'))[0]
    assert 'pre_tasks' in playbook
    assert not playbook['vars']
    assert 'container_service' in playbook['roles']

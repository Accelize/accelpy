# coding=utf-8
"""Host configuration tests"""
import pytest


def test_host(tmpdir):
    """
    Test host

    Args:
        tmpdir (py.path.local) tmpdir pytest fixture
    """
    import accelpy._common as common
    import accelpy._host as accelpy_host
    from accelpy._host import Host, iter_hosts
    from accelpy.exceptions import ConfigurationException
    from accelpy._application import Application

    from tests.test_core_terraform import mock_terraform_provider
    from tests.test_core_packer import mock_packer_provider
    from tests.test_core_ansible import mock_ansible_local
    from tests.test_core_application import mock_application

    source_dir = tmpdir.join('source').ensure(dir=True)

    # Mock ~/.accelize
    common_home_dir = common.HOME_DIR
    common.HOME_DIR = tmpdir.join('home').ensure(dir=True)

    # Mock config dir
    accelpy_host_config_dir = accelpy_host.CONFIG_DIR
    config_dir = tmpdir.join('config').ensure(dir=True)
    accelpy_host.CONFIG_DIR = str(config_dir)

    # Mock application definition file & provider specific configuration
    application = mock_application(source_dir)
    mock_terraform_provider(source_dir)
    artifact = mock_packer_provider(source_dir)
    source_dir.ensure('cred.json')

    # Tests
    try:

        # Test: Host generation with not arguments should raise
        with pytest.raises(ConfigurationException):
            Host()

        # Test: Create host with specified name + use as context manager
        name = 'testing'
        with Host(application=application, name=name,
                  user_config=source_dir) as host:
            assert host.name == name
            assert name in str(host)
            assert name in repr(host)

        # Test: Create host with generated name
        host = Host(application=application, user_config=source_dir)
        assert host.name
        name = host.name

        # Test: Initialization
        host_config_dir = config_dir.join(name)
        assert host_config_dir.join('playbook.yml').isfile()
        assert host_config_dir.join('common.tf').isfile()
        assert host_config_dir.join('template.json').isfile()
        assert host_config_dir.join('application.yml').isfile()
        assert host._ansible
        assert host._application
        assert host._terraform
        assert host._packer

        # Test: Output values should raise as not applied
        with pytest.raises(ConfigurationException):
            assert host.private_ip

        # Test: Terraform plan
        assert host.plan()

        # Test: Output values should still raise if only planned
        with pytest.raises(ConfigurationException):
            assert host.private_ip

        # Test: Terraform apply
        host.apply(quiet=True)
        assert host_config_dir.join('terraform.tfstate').isfile()

        # Test: Output variable
        assert host.private_ip == "127.0.0.1"
        assert host.public_ip == "127.0.0.1"
        assert host.ssh_user == "user"
        assert host.ssh_private_key == str(
            host_config_dir.join('ssh_private.pem'))

        # Test: Terraform destroy
        host.destroy(quiet=True, delete=True)

        # Test: Do destroy on exit
        with Host(application=application, user_config=source_dir,
                  destroy_on_exit=True, keep_config=False) as host:

            assert not config_dir.join(
                f'{host.name}/terraform.tfstate').isfile()

            host.apply(quiet=True)
            assert config_dir.join(f'{host.name}/terraform.tfstate').isfile()

        assert not config_dir.join(host.name).exists()

        # Test: Do not destroy on exit
        with Host(application=application, user_config=source_dir) as host:
            host_not_destroyed = host.name
            host.apply(quiet=True)
            assert config_dir.join(f'{host.name}/terraform.tfstate').isfile()

        assert config_dir.join(f'{host.name}/terraform.tfstate').isfile()

        # Test: Do not destroy on exit, but do not keep un-applied config
        with Host(application=application, user_config=source_dir,
                  keep_config=False) as host:
            assert config_dir.join(host.name).exists()

        assert not config_dir.join(host.name).exists()

        # Test: Clean up in case of initialization error
        with pytest.raises(ConfigurationException):
            Host(application='path_not_exists', user_config=source_dir,
                 name='should_be_cleaned')
        assert not config_dir.join('should_be_cleaned').exists()

        # Test: Load existing host
        with Host(name=host_not_destroyed) as host:
            assert host.private_ip
            assert host._application

        # Test: Iter over host
        config_dir.join('latest').ensure()
        assert host_not_destroyed in tuple(host.name for host in iter_hosts())

        # Test: Build image
        provider = 'testing'
        with Host(application=application, user_config=source_dir,
                  provider=provider) as host:

            # Mock ansible playbook
            host_config_dir = config_dir.join(host.name)
            mock_ansible_local(host_config_dir)

            application_yaml = str(host_config_dir.join('application.yml'))

            # Test: Build image and with no application update
            assert Application(application_yaml).get(
                'package', 'name', env=provider) == 'my_image'

            host.build(quiet=True)

            assert Application(application_yaml).get(
                'package', 'name', env=provider) == 'my_image'

            # Test: Build image and update application
            host.build(quiet=True, update_application=True)

            assert Application(application_yaml).get(
                'package', 'name', env=provider) == artifact

        # Test: Missing Accelize DRM configuration
        application = mock_application(
            source_dir, override={'accelize_drm': {}})

        with pytest.raises(ConfigurationException):
            Host(application=application, user_config=source_dir,
                 keep_config=False)

        # Test: Missing Accelize DRM credentials
        source_dir.join('cred.json').remove()
        application = mock_application(source_dir)
        with pytest.raises(ConfigurationException):
            Host(application=application, user_config=source_dir,
                 keep_config=False)

    # Restore mocked config dir
    finally:
        accelpy_host.CONFIG_DIR = accelpy_host_config_dir
        common.HOME_DIR = common_home_dir

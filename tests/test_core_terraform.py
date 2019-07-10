# coding=utf-8
"""Terraform handler tests"""
import pytest


def mock_terraform_provider(source_dir, **variables):
    """
    Mock provider configuration

    Args:
        source_dir (py.path.local) Source directory.
        variables: Override local variables.

    Returns:
        dict: Input variables.
    """
    from accelpy._common import json_write

    local_variables = {
        "host_public_ip": "127.0.0.1",
        "host_private_ip": "127.0.0.1",
        "remote_user": 'user',
        "accelize_drm_driver_name": "driver"
    }
    json_write({
        "locals": local_variables
    }, source_dir.join('common.testing.tf.json'))

    if variables:
        json_write({
            "locals": variables
        }, source_dir.join('common.testing_override.tf.json'))

    local_variables.update(variables)
    return local_variables


def test_terraform(tmpdir):
    """
    Test Terraform handler

    Args:
        tmpdir (py.path.local) tmpdir pytest fixture
    """
    from accelpy._terraform import Terraform
    from accelpy.exceptions import RuntimeException

    config_dir = tmpdir.join('config').ensure(dir=True)
    source_dir = tmpdir.join('source').ensure(dir=True)
    generated_ssh_key = config_dir.join('ssh_private.pem')

    # Mock provider specific Terraform configuration
    local_variables = mock_terraform_provider(source_dir)

    # Test: Create configuration (With not specific provider and application)
    terraform = Terraform(
        config_dir, variables=dict(host_name='testing'), user_config=source_dir)
    terraform.create_configuration()

    # Test: Re-create should not raise
    terraform.create_configuration()

    # Test: Plan should not raise on basic configuration
    assert terraform.plan()

    # Test: state_list should return empty list if not applied
    assert not terraform.state_list()

    # Test: Refresh should do nothing if no state file
    terraform.refresh(quiet=True)

    # Test: Apply should only generate a SSH key
    terraform.apply(quiet=True)
    assert generated_ssh_key.isfile()

    # Test: State list should return state content
    assert 'local_file.ssh_key_generated_pem[0]' in terraform.state_list()

    # Test: Output
    output = terraform.output
    assert output['host_ssh_private_key'] == './ssh_private.pem'
    for key, value in local_variables.items():
        if key not in ('accelize_drm_driver_name',):
            assert output[key] == value, f'"{key}"" in output result'

    # Test: Refresh should not raise with state file
    terraform.refresh(quiet=True)

    # Test: Destroy should remove SSH key
    terraform.destroy(quiet=True)
    assert not generated_ssh_key.exists()

    # Test: state list should raise on Terraform error (Ex corrupted state file)
    assert not terraform.state_list()
    config_dir.join('terraform.tfstate').write(b'invalid_state_file')
    with pytest.raises(RuntimeException):
        terraform.state_list()

    # Mock Terraform util to simulate errors
    exception_message = "Not retryable error"

    class FakeTerraform(Terraform):
        """Fake Terraform"""

        @staticmethod
        def _exec(*args, **_):
            """
            Fake calls that raise exceptions on "apply"
            """
            if 'apply' in args:
                raise RuntimeException(exception_message)

    terraform = FakeTerraform(
        config_dir, variables=dict(host_name='testing'), user_config=source_dir)

    # Test: Apply should not retry if not retryable known error
    with pytest.raises(RuntimeException) as excinfo:
        terraform.apply(retries=3, delay=0.01)
    assert 'Unable to apply after ' not in str(excinfo)

    # Test: Apply should retry if retryable known error
    exception_message = 'Error while waiting for spot request'
    with pytest.raises(RuntimeException) as excinfo:
        terraform.apply(retries=3, delay=0.01)
    assert excinfo.match('Unable to apply after ')


def test_common_configuration(tmpdir):
    """
    Test Terraform "common.tf"

    Args:
        tmpdir (py.path.local): tmpdir pytest fixture
    """
    from accelpy._terraform import Terraform
    from accelpy._common import call
    from accelpy.exceptions import RuntimeException

    config_dir = tmpdir.join('config').ensure(dir=True)
    source_dir = tmpdir.join('source').ensure(dir=True)

    # Test: Default generated SSH key
    mock_terraform_provider(source_dir)

    terraform = Terraform(config_dir, user_config=source_dir)
    terraform.create_configuration()
    terraform.apply(quiet=True)

    assert terraform.output['host_ssh_private_key'] == './ssh_private.pem'

    # Test: Use user provided SSH private key
    user_ssh_key = str(tmpdir.join('user_key.pem'))
    call(['ssh-keygen', '-t', 'ecdsa', '-f', user_ssh_key, '-N', ''],
         pipe_stdout=True)

    config_dir.remove(rec=1)
    config_dir.ensure(dir=True)
    mock_terraform_provider(source_dir, ssh_key_pem=str(user_ssh_key))

    terraform = Terraform(config_dir, user_config=source_dir)
    terraform.create_configuration()
    try:
        terraform.apply(quiet=True)
    except RuntimeException as exc:
        # Sometime, Fails with the test provided key (With OpenSSH 8.0/Fedora30)
        # Todo: Find exactly what is wrong
        if 'failed to decode PEM block containing private key' in str(exc):
            pytest.xfail('Incompatible private Key')
        raise

    assert terraform.output['host_ssh_private_key'] == str(user_ssh_key)

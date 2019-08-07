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
        "remote_os": "os",
        "provider_required_driver": "driver",
        "require_ask_pass": "false"
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
    terraform = Terraform(config_dir)
    terraform.create_configuration(
        variables=dict(host_name='testing'), user_config=source_dir)

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
        if key not in ('provider_required_driver', 'remote_os',
                       'require_ask_pass'):
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

        @classmethod
        def _name(cls):
            """Use correct name."""
            return 'terraform'

        @staticmethod
        def _exec(*args, **_):
            """
            Fake calls that raise exceptions on "apply"
            """
            if 'apply' in args:
                raise RuntimeException(exception_message)

    terraform = FakeTerraform(config_dir)
    terraform.create_configuration(
        variables=dict(host_name='testing'), user_config=source_dir)

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
    from os import chmod
    from accelpy._terraform import Terraform

    config_dir = tmpdir.join('config').ensure(dir=True)
    source_dir = tmpdir.join('source').ensure(dir=True)

    # Test: Default generated SSH key
    mock_terraform_provider(source_dir)

    terraform = Terraform(config_dir)
    terraform.create_configuration(user_config=source_dir)
    terraform.apply(quiet=True)

    assert terraform.output['host_ssh_private_key'] == './ssh_private.pem'

    # Test: Use user provided SSH private key
    user_ssh_key = str(tmpdir.join('user_key.pem'))
    with open(user_ssh_key, 'wb') as key_file:
        # RSA 1024 key
        key_file.write(
            b"-----BEGIN RSA PRIVATE KEY-----\n"
            b"MIICXQIBAAKBgQC1gOpjs0RIAJm1/t07vSBhFZtD7KX8qFoH2XE+Ry3lbIKNKBpK"
            b"9EYNdf/MYlekedHcZUz6UXoPBCrEkJmawrkz/L1Vczz/LiaEcKYgzYd3jciQ5/o5"
            b"6tGfdzAC98+7NtzfXMg8utdW9cqTBUkRTR0UW092eutPJHAYPiIZN3bVuQIDAQAB"
            b"AoGANGsBxj9sldrOiZgMbodFRaSGzcwXd+tq7N9obBMEd0CqR3fwd/sqDBMrB+zS"
            b"4OZprFv5KkXDmXibnV8hbWeVMqi0wKCj3KNYgpvya/ReukD+CbDGrnRZs7iFyGQF"
            b"qKFOPqd7JcXVPDj5PWFPOI8PvFtikxa80Gx35uaxOwAnSt0CQQDj71MGVlDTkmem"
            b"6kZ/A9F/oa1TgbqYvlovF8oofftAN98c+QSbP2d2cTNUcxgA8Q1lmIPbgEouJXbB"
            b"Ahs08F4bAkEAy9oK9GvnrDem1pG4wJt/3NVcU3KmsX8jASw9tXGwSac0yV41f+xO"
            b"y975sy5hFu5YNO84uNIOPKJQB32YCOfIuwJAMrK7w9AVIEoTNgQr8/p0cbATblyP"
            b"lYPZaVogRAtphCopPTeCN8nNiIG7ShBjiWoUccGPqpYJaeQ5WsrOJGNGewJBAJ5J"
            b"SIhR4SpQbDPgIt0r4TTQV0hUlirs1XlrqN7i0EfglZRmmpQiIW0cTjdbo/fySnuP"
            b"5TNdp8BdKFcopo0DrVECQQDMGk2sZikHXPbawNgQdYbyIwl2AznyvsVFxBzIP3u3"
            b"sdw+GZisEbUY0Uqt+XvCqibcjivRcT7j5Xh6ljTg5ChF"
            b"\n-----END RSA PRIVATE KEY-----\n")
    chmod(user_ssh_key, 0o600)

    config_dir.remove(rec=1)
    config_dir.ensure(dir=True)
    mock_terraform_provider(source_dir, ssh_key_pem=str(user_ssh_key))

    terraform = Terraform(config_dir)
    terraform.create_configuration(user_config=source_dir)
    terraform.apply(quiet=True)

    assert terraform.output['host_ssh_private_key'] == str(user_ssh_key)

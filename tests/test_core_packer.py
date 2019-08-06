# coding=utf-8
"""Packer handler tests"""


def mock_packer_provider(source_dir):
    """
    Mock provider configuration

    Args:
        source_dir (py.path.local) Source directory.

    Returns:
        str: artifact
    """
    from accelpy._json import json_write
    artifact = "artifact.json"
    json_write({
        "builders": [{
            "type": "file",
            "content": "",
            "target": artifact
        }]}, source_dir.join('testing.json'))
    return artifact


def test_packer(tmpdir):
    """
    Test Packer handler

    Args:
        tmpdir (py.path.local) tmpdir pytest fixture
    """
    from accelpy._json import json_read
    from accelpy._packer import Packer

    from tests.test_core_ansible import mock_ansible_local

    config_dir = tmpdir.join('config').ensure(dir=True)
    source_dir = tmpdir.join('source').ensure(dir=True)
    variables = dict(key='value', template='{{ key }}', to_delete=1)

    # Mock provider specific Packer builder
    artifact = mock_packer_provider(source_dir)

    # Mock Ansible playbook required to provision
    mock_ansible_local(config_dir)

    # Test: Create configuration (With not specific provider and application)
    packer = Packer(config_dir)
    packer.create_configuration(
        variables=variables, provider='testing', user_config=source_dir)

    # Test: check Jinja template correctly evaluated
    template = json_read(config_dir.join('template.json'))
    assert template['variables']['key'] == template['variables']['template']
    assert 'to_delete' not in template['variables']

    # Test: Re-create should not raise
    packer.create_configuration(
        variables=variables, provider='testing', user_config=source_dir)

    # Test: Validate should not raise on basic configuration
    packer.validate()

    # Test: Build
    manifest = packer.build(quiet=True)
    assert manifest['builder_type'] == 'file'
    packer_run_uuid = manifest['packer_run_uuid']

    # Test: Build another time should select the proper run UUID
    manifest = packer.build(quiet=True)
    assert manifest['packer_run_uuid'] != packer_run_uuid
    assert packer_run_uuid in config_dir.join(
        'packer-manifest.json').read_text('utf-8')

    # Test: get file artifact
    assert packer.get_artifact(manifest) == artifact

    # Test: AWS AMI artifact
    assert packer.get_artifact(
        dict(builder_type='amazon-ebs',
             artifact_id='region:ami-id')) == 'ami-id'

    # Test: Default to artifact ID
    assert packer.get_artifact(
        dict(builder_type='not_exist_builder',
             artifact_id='artifact_id')) == 'artifact_id'

# coding=utf-8
"""HashiCorp common functions tests"""
import pytest


def test_utility(tmpdir):
    """
    Test Utility

    Args:
        tmpdir (py.path.local) tmpdir pytest fixture
    """
    from os.path import getctime, getmtime, join
    from os import fsdecode
    from accelpy._hashicorp import Utility
    from accelpy.exceptions import RuntimeException
    from accelpy._common import HOME_DIR

    # Mock utility to use temporary install directory
    install_dir = tmpdir.join('install').ensure(dir=True)
    config_dir = tmpdir.join('config').ensure(dir=True)

    class Terraform(Utility):
        """Terraform utility"""

        @classmethod
        def _install_dir(cls):
            """
            Install directory.

            Returns:
                str: Install directory.
            """
            return fsdecode(install_dir)

    utility = Terraform(config_dir)

    # Test: Mocked property
    assert Utility._install_dir() == join(HOME_DIR, 'utility')

    # Test: Retrieve information and test HashiCorp fields presence
    last_release = Terraform._get_last_version()
    assert 'current_version' in last_release
    assert 'current_download_url' in last_release

    # Test: Download executable if not exists
    assert Terraform._executable is None
    exec_file = utility._get_executable()
    assert Terraform._executable == exec_file

    # Test: Run executable
    version = utility._exec('version', pipe_stdout=True).stdout.strip()
    assert version.lower().startswith('terraform')
    assert version.lower().endswith(utility.version)
    assert utility.version == last_release['current_version']

    # Test: executable not downloaded if already exists and up to date
    Terraform._executable = None
    ctime = getctime(exec_file)
    mtime = getmtime(exec_file)

    exec_file_2 = utility._get_executable()

    assert exec_file == exec_file_2
    if version == utility._exec('version', pipe_stdout=True).stdout.strip():
        # Already up to date
        assert ctime == getctime(exec_file_2)
        assert mtime == getmtime(exec_file_2)

    # Test: Run executable and redirect stdout
    assert not utility._exec('version').stdout
    assert utility._exec('version', pipe_stdout=True).stdout

    # Test: Run and raise exception on error
    with pytest.raises(RuntimeException):
        utility._exec('bad_command',
                      # Avoid output on pytest result
                      pipe_stdout=True)

    # Test: Run and ignore error
    utility._exec('bad_command', check=False,
                  # Avoid output on pytest result
                  pipe_stdout=True)

    # Test: Valid GPG signature
    checksum_raw = utility._download(last_release['checksum_url']).content
    checksum_sig_raw = utility._download(last_release['signature_url']).content
    Terraform._gpg_verify(checksum_raw, checksum_sig_raw)

    # Test: Invalid GPG signature
    with pytest.raises(RuntimeException) as exception:
        Terraform._gpg_verify(checksum_raw + b'0', checksum_sig_raw)
    assert exception.match('Unable to update terraform: Invalid signature')

    # Test: Valid checksum
    data = utility._download(last_release['archive_url']).content
    utility._checksum_verify(
        checksum_raw, data, last_release['archive_name'])

    # Test: Invalid checksum
    with pytest.raises(RuntimeException) as exception:
        utility._checksum_verify(
            checksum_raw, data + b'0', last_release['archive_name'])
    assert exception.match('Unable to update terraform: Invalid checksum')

    # Test: Checksum for file missing in checksum list
    with pytest.raises(RuntimeException) as exception:
        utility._checksum_verify(checksum_raw, data, 'do_not_exist')
    assert exception.match('Unable to update terraform: No checksum found')

    # Test: Download failure
    with pytest.raises(RuntimeException):
        utility._download(
            last_release['current_download_url'] + 'do_not_exist')

# coding=utf-8
"""HashiCorp utilities common functions"""
from os import chmod, stat, makedirs, fsdecode, scandir
from os.path import join, isfile, dirname, getmtime
from time import time

from accelpy._common import (
    HOME_DIR, call, get_sources_dirs, get_sources_filters)
from accelpy._json import json_read, json_write
from accelpy.exceptions import RuntimeException


class Utility:
    """
    Base class for all HashiCorp utility

    Args:
        config_dir (path-like object): Configuration directory.
    """
    # Memoized executable path
    _executable = None

    # To override with __file__ in subclasses for good directory detection
    _FILE = __file__

    # Files extensions
    _EXTS_INCLUDE = ()
    _EXTS_EXCLUDE = ()

    def __init__(self, config_dir):
        self._config_dir = fsdecode(config_dir)

    @classmethod
    def _name(cls):
        """
        Utility name

        Returns:
            str: Utility name
        """
        return cls.__name__.lower()

    @classmethod
    def _install_dir(cls):
        """
        Install directory.

        Returns:
            str: Install directory.
        """
        return join(HOME_DIR, cls._name())

    @classmethod
    def _get_executable(cls):
        """
        Get utility executable path after installing or updating it if
        required.
        """
        if not cls._executable:
            # Get utility release information from HashiCorp checkpoint API
            last_release = cls._get_last_version()

            # Check if executable is already installed and up-to-date
            cls._executable = exec_file = join(
                cls._install_dir(), last_release['executable_name'])

            if isfile(exec_file):
                line = call((exec_file, 'version'),
                            pipe_stdout=True).stdout.splitlines()[0]
                exec_version = line.split(' ')[1].strip().lstrip('v')

                # If file is installed and up-to-date, returns its path
                if exec_version == last_release['current_version']:
                    return exec_file

            # Download executables checksum file and associated signature
            checksum_raw = cls._download(last_release['checksum_url']).content
            checksum_sig_raw = cls._download(
                last_release['signature_url']).content

            # Verify checksum file signature against HashiCorp GPG key
            cls._gpg_verify(checksum_raw, checksum_sig_raw)

            # Download the latest compressed executable
            compressed = cls._download(last_release['archive_url']).content

            # Verify executable checksum
            cls._checksum_verify(
                checksum_raw, compressed, last_release['archive_name'])

            # Ensure directories exists
            makedirs(cls._install_dir(), exist_ok=True)

            # Lazy import package that are required only on install
            from io import BytesIO
            from zipfile import ZipFile

            # Extract executable and returns its path
            compressed_file_obj = BytesIO(compressed)
            compressed_file_obj.seek(0)
            with ZipFile(compressed_file_obj) as compressed_file:
                cls._executable = compressed_file.extract(
                    compressed_file.namelist()[0], path=cls._install_dir())

            # Ensure the file is executable
            chmod(cls._executable, stat(cls._executable).st_mode | 0o111)

        return cls._executable

    @classmethod
    def _download(cls, url):
        """
        Download from URL and handles exceptions.

        Args:
            url (str): URL

        Returns:
            requests.Response: Response.

        Raises:
            accelpy.exceptions.RuntimeException: HTTP Error.
        """
        # Lazy import: Only used on update
        from requests import get
        from requests.exceptions import HTTPError

        response = get(url)

        try:
            response.raise_for_status()
        except HTTPError as error:
            raise RuntimeException(
                f'Unable to update {cls._name()}: {str(error)}')

        return response

    @classmethod
    def _get_last_version(cls):
        """
        Get last version information from HashiCorp checkpoint API.

        Returns:
            dict: Last version information.
        """
        info_cache = join(cls._install_dir(), 'info.json')

        # Get Last version information from HashiCorp checkpoint API
        if not isfile(info_cache) or getmtime(info_cache) < time() - 3600.0:

            # Lazy import: Only used on update
            from platform import machine, system

            # Update from the web
            last_release = cls._download(
                'https://checkpoint-api.hashicorp.com/v1/check/' +
                cls._name()).json()

            current_version = last_release['current_version']
            download_url = last_release['current_download_url'].rstrip('/')

            # Define platform specific utility executable and archive name
            arch = machine().lower()
            arch = {'x86_64': 'amd64'}.get(arch, arch)

            last_release['archive_name'] = archive_name = \
                f"{cls._name()}_{current_version}_{system().lower()}_{arch}.zip"

            last_release['executable_name'] = \
                f'{cls._name()}.exe' if system() == 'Windows' else cls._name()

            # Define download URL
            last_release['archive_url'] = f"{download_url}/{archive_name}"
            last_release['checksum_url'] = checksum_url = \
                f"{download_url}/{cls._name()}_{current_version}_SHA256SUMS"
            last_release['signature_url'] = f"{checksum_url}.sig"

            # Cache result
            makedirs(cls._install_dir(), exist_ok=True)
            json_write(last_release, info_cache)

        else:
            # Get cached version
            last_release = json_read(info_cache)

        return last_release

    @classmethod
    def _checksum_verify(cls, checksum_list, data, filename):
        """
        Verify SHA256 checksum

        Args:
            checksum_list (bytes): List of checksum. Should have one
                line per file formatted as "digest filename".
            data (bytes): Data to verify.
            filename (str): Name of file to verify

        Raises:
            accelpy.exceptions.RuntimeException: Invalid Checksum.
        """
        # Get file checksum in checksum file
        for line in checksum_list.decode().splitlines():
            if filename in line:
                checksum = line.split(' ')[0].strip()
                break
        else:
            # Should never raise
            raise RuntimeException(
                f'Unable to update {cls._name()}: No checksum found')

        # Lazy import package that are required only on install
        from hashlib import sha256

        # Verify checksum
        sha = sha256()
        sha.update(data)
        if sha.hexdigest() != checksum:
            raise RuntimeException(
                f'Unable to update {cls._name()}: Invalid checksum')

    @classmethod
    def _gpg_verify(cls, data, signature):
        """
        Verify GPG signature with HashiCorp public key.

        Args:
            data (bytes): Data to verify.
            signature (bytes): Signature against verify data.

        Raises:
            accelpy.exceptions.RuntimeException: Invalid signature.

        References:
            https://www.hashicorp.com/security.html
        """
        # Import HashiCorp GPG public key
        call(('gpg', '--import', join(dirname(__file__), 'gpg_public_key.asc')),
             pipe_stdout=True)

        # Lazy import package that are required only on install
        from tempfile import TemporaryDirectory

        # Verify signature
        with TemporaryDirectory() as tmp:

            data_path = join(tmp, 'data')
            with open(data_path, 'wb') as data_file:
                data_file.write(data)

            signature_path = join(tmp, 'data.sig')
            with open(signature_path, 'wb') as signature_file:
                signature_file.write(signature)

            gpg_valid = call(('gpg', '--verify', signature_path, data_path),
                             pipe_stdout=True, check=False)

        if gpg_valid.returncode:
            raise RuntimeException(
                f'Unable to update {cls._name()}: Invalid signature')

    def _exec(self, *args, check=True, pipe_stdout=False, **run_kwargs):
        """
        Call utility.

        Args:
            args: Utility positional arguments.
            run_kwargs: subprocess
            check (bool): If True, Check return code for error.
            pipe_stdout (bool): If True, redirect stdout into a pipe, this allow
                to hide outputs from sys.stdout and permit to retrieve stdout as
                "result.stdout".

        Returns:
            subprocess.CompletedProcess: Utility call result.
        """
        return call([self._get_executable()] + [arg for arg in args if arg],
                    cwd=self._config_dir, check=check, pipe_stdout=pipe_stdout,
                    **run_kwargs)

    def _list_sources(self, provider, application_type, user_config):
        """
        List source files matching current configuration.

        Args:
            provider (str): Provider name.
                Required only if no "host_id" provided.
            application_type (str): Application type.
            user_config (path-like object): User configuration directory.
                Required only if no "host_id" provided.

        Yields:
            tuple of str: name and path to source files.
        """
        names = get_sources_filters(provider, application_type)
        excludes = self._EXTS_EXCLUDE
        includes = self._EXTS_INCLUDE
        for source_dir in get_sources_dirs(dirname(self._FILE), user_config):
            with scandir(source_dir) as entries:
                for entry in entries:
                    name = entry.name.lower()
                    if (entry.is_file() and
                        name.split('.', 1)[0] in names and
                            any(name.endswith(include)
                                for include in includes) and
                            all(not name.endswith(exclude)
                                for exclude in excludes)):
                        yield name, entry.path

    @property
    def version(self):
        """
        Return utility version.

        Returns:
            str: version
        """
        return self._exec('version', pipe_stdout=True).stdout.strip().rsplit(
                          maxsplit=1)[-1].lstrip('v')

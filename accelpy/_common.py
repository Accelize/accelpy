# coding=utf-8
"""Global configuration"""
from importlib import import_module as _import_module
from json import (load as _json_load, JSONDecodeError as _JSONDecodeError,
                  dump as _json_dump)
from os import (fsdecode as _fsdecode, symlink as _symlink, chmod as _chmod,
                makedirs as _makesdirs, scandir as _scandir,
                listdir as _listdir, environ as _environ, remove as _remove)
from os.path import (
    expanduser as _expanduser, isdir as _isdir, realpath as _realpath,
    join as _join, dirname as _dirname, basename as _basename,
    isfile as _isfile, splitext as _splitext)
from subprocess import run as _run, PIPE as _PIPE
from time import time as _time

from accelpy.exceptions import (
    RuntimeException as _RuntimeException,
    AuthenticationException as _AuthenticationException,
    ConfigurationException as _ConfigurationException,
    WebServerException as _WebServerException)

#: User configuration directory
HOME_DIR = _expanduser('~/.accelize')

# Cached values storage
_cache = dict()
CACHE_DIR = _join(HOME_DIR, '.cache')

# Ensure directory exists and have restricted access rights
_makesdirs(CACHE_DIR, exist_ok=True)
_chmod(HOME_DIR, 0o700)


def json_read(path, **kwargs):
    """
    Read a JSON file.

    Args:
        path (path-like object): Path to file to load.
        kwargs: "json.load" kwargs.

    Returns:
        dict or list: Un-serialized content
    """
    path = _realpath(_fsdecode(path))
    with open(path, 'rt') as file:
        try:
            return _json_load(file, **kwargs)

        except _JSONDecodeError as exception:
            raise _ConfigurationException(
                f'Unable to read "{path}": {str(exception)}')


def json_write(data, path, **kwargs):
    """
    Write a JSON file

    Args:
        data (dict or list): data to serialize.
        path (path-like object): Path where save file.
        kwargs: "json.dump" kwargs.
    """
    with open(_fsdecode(path), 'wt') as file:
        _json_dump(data, file, **kwargs)


def recursive_update(to_update, update):
    """
    Recursively updates nested directories.

    Args:
        to_update (dict or collections.Mapping):
            dict to update.
        update (dict or collections.Mapping):
            dict containing new values.

    Returns:
        dict: to_update
    """
    if update:
        for key, value in update.items():
            if isinstance(value, dict):
                value = recursive_update(to_update.get(key, {}), value)
            to_update[key] = value
    return to_update


def call(command, check=True, pipe_stdout=False, retries=0, **run_kwargs):
    """
    Call command in subprocess.

    Args:
        command (iterable of str): Command
        run_kwargs: subprocess.run keyword arguments.
        check (bool): If True, Check return code for error.
        pipe_stdout (bool): If True, redirect stdout into a pipe, this allow to
            hide outputs from sys.stdout and permit to retrieve stdout as
            "result.stdout".
        retries (int): If True, retry this number of time on error.

    Returns:
        subprocess.CompletedProcess: Utility call result.
    """
    kwargs = dict(universal_newlines=True, stderr=_PIPE)
    kwargs.update(run_kwargs)

    if pipe_stdout:
        kwargs.setdefault('stdout', _PIPE)

    retried = 0
    while True:
        result = _run(command, **kwargs)

        if result.returncode and retried < retries:
            retried += 1
            continue
        break

    if check and result.returncode:
        raise _RuntimeException('\n'.join((
            'Error while running:', ' '.join(command), '',
            (result.stderr or result.stdout or
             warn('See stdout for more information.')).strip())))

    return result


def get_sources_dirs(*src):
    """
    Return sources directories.

    Args:
        *src: Directories paths.

    Returns:
        list of str: Sources directories
    """
    paths = [HOME_DIR, '.']
    paths.extend(src)
    return [_realpath(_fsdecode(path)) for path in paths if path]


def symlink(src, dst):
    """
    Extended "os.symlink" that:
    - Autodetect if target is directory.
    - Ignore error if file already exists.
    - Ensure to link to real absolute path of the source.

    Args:
        src (path-like object): Source path.
        dst (path-like object): Destination path.
    """
    src = _realpath(_fsdecode(src))
    try:
        _symlink(src, _fsdecode(dst), target_is_directory=_isdir(src))
    except FileExistsError:
        pass


def get_sources_filters(provider, application):
    """
    Return names to use to filer sources

    Args:
        provider (str): provider name.
        application (str): Application type.

    Returns:
        list of str: sources names
    """
    provider = provider or ''
    return [key for key in
            ('common', provider.split(',')[0], application) if key]


def get_python_package_entry_point(package, entry_point):
    """
    Find an CLI entry point from a Python package.

    Args:
        package (str): Package name.
        entry_point (str): Entry point name.

    Returns:
        str or None: Path to entry point, or None if nothing found.
    """
    site_packages_path = _dirname(_import_module(package).__path__[0])

    # Find package info
    # Can be a directory ending by ".dist-info" or ".egg-info"
    with _scandir(site_packages_path) as entries:
        for entry in entries:
            if (entry.name.startswith(f'{package}-') and
                    _splitext(entry.name)[1] in ('.dist-info', '.egg-info')):
                package_info_path = entry.path
                break

        else:
            # Package is not installed or do not have package info
            return None

    # Find manifest file
    # Can be a "RECORD" or a "installed-files.txt" file in package info folder
    for name in ('RECORD', 'installed-files.txt'):
        manifest_path = _join(package_info_path, name)
        if _isfile(manifest_path):
            break

    else:
        # Package do not have manifest file
        return None

    # Find entry point relative path in manifest file
    # Possibles manifest file lines formats: "path\n" or "path,checksum\n"
    with open(manifest_path, 'rt') as manifest:

        for line in manifest:
            entry_point_rel_path = line.strip().split(',', 1)[0]
            if _basename(entry_point_rel_path) == entry_point:
                break

        else:
            # Entry point is not present in manifest
            return None

    # Convert to absolute path
    # Paths in manifest are relative to site-packages or package info
    for prefix in (site_packages_path, package_info_path):
        entry_point_path = _realpath(_join(prefix, entry_point_rel_path))

        if _isfile(entry_point_path):
            return entry_point_path


def no_color():
    """
    If "ACCELPY_NO_COLOR" environment variable is set, return True.

    Returns:
        bool: True if no color mode.
    """
    return bool(_environ.get("ACCELPY_NO_COLOR", False))


def debug():
    """
    If "ACCELPY_DEBUG" environment variable is set, return True.

    Returns:
        bool: True if debug mode.
    """
    return bool(_environ.get("ACCELPY_DEBUG", False))


def is_cli():
    """
    Return True if CLI.

    Returns:
        bool: True if debug mode.
    """
    return bool(_environ.get("ACCELPY_CLI", False))


def color_str(text, color):
    """
    Format text as colored output.

    Args:
        text (str): text.
        color (str): color.

    Returns:
        str: Colored text.
    """
    # Disable color output if not in CLI mode or if color is disabled
    if not is_cli() or no_color():
        return text

    # Lazy import colorama only if required and skip if not available.
    try:
        from colorama import init, Fore
    except ImportError:  # pragma: no cover
        return text

    # Init colorama if not already done
    if not _cache.get('colorama_initialized'):
        init()
        _cache['colorama_initialized'] = True

    # Return colored output
    return f'{getattr(Fore, color)}{text}{Fore.RESET}'


def error(text):
    """
    Return error colored output.

    Args:
        text (str): text.

    Returns:
        str: Colored text.
    """
    return color_str(text, 'RED')


def warn(text):
    """
    Return warning colored output.

    Args:
        text (str): text.

    Returns:
        str: Colored text.
    """
    return color_str(text, 'YELLOW')


def get_accelize_cred(*src):
    """
    Initialize Accelize Credentials.

    Args:
        src (str): Directories.

    Returns:
        str: Path to cred.json
    """
    for src in get_sources_dirs(*src):
        cred_path = _join(src, 'cred.json')
        if _isfile(cred_path):
            return cred_path

    raise _AuthenticationException(
        'No Accelize credential found. Please, make sure to have your '
        f'"cred.json" file installed in "{HOME_DIR}" or current directory')


def hash_cli_name(name):
    """
    Convert name to SHA1 hashed name.

    Args:
        name (str): name.

    Returns:
        str: Hashed name.
    """
    from hashlib import blake2b
    return blake2b(name.encode(), digest_size=32).hexdigest()


def get_cli_cache(name, recursive=False):
    """
    Get an object from disk cache.

    Args:
        name (str): Cache name.
        recursive (bool): If True, recursively search for cached values
            starting by various "name" prefixes.

    Returns:
        dict or list or None: object, None if object is not cached.
    """
    if not is_cli():
        return None

    # List cached values candidates
    timestamp = _time()
    candidates = {}
    for filename in _listdir(CACHE_DIR):
        path = _join(CACHE_DIR, filename)
        cached_name, expiry = filename.rsplit('_', 1)

        # Remove expired cached files
        if int(expiry) < timestamp:
            try:
                _remove(path)
                continue
            except OSError:  # pragma: no cover
                # Should never raise, May be already removed by another accelpy
                # instance
                continue

        # Memorize candidates cached files
        candidates[cached_name] = path

    if not candidates:
        return

    # Get cached value, or return None
    if recursive:
        names = []
        while name and not name.endswith('|'):
            names.append(name)
            name = name[:-1]
        names.append(name)

    else:
        names = name,

    for hashed_name in (hash_cli_name(name) for name in names):
        try:
            return json_read(candidates[hashed_name])
        except KeyError:
            continue


def set_cli_cache(name, obj, expiry_timestamp=None, expiry_seconds=30):
    """
    Add an object to disk cache. Mainly used to avoid repeated web server
    requests in CLI mode.

    Args:
        name (str): Cache name.
        obj (dict or list): Object to cache.
        expiry_timestamp (int): Expiry timestamp.
        expiry_seconds (int): Number of seconds before expiration.

    Returns:
        dict or list: obj
    """
    if not is_cli():
        return obj

    if expiry_timestamp is None:
        expiry_timestamp = int(_time()) + expiry_seconds

    path = _join(CACHE_DIR, f"{hash_cli_name(name)}_{int(expiry_timestamp)}")
    json_write(obj, path)
    _chmod(path, 0o600)

    return obj


class _AccelizeWSSession:
    """
    Accelize Web Service session.
    """
    _TIMEOUT = 10
    _RETRIES = 3
    _ENDPOINT = 'https://master.metering.accelize.com'

    def __init__(self):
        self._token_expire = 0
        self._token = ''
        self._session = None
        self._session_request = None
        self._endpoint = self._ENDPOINT

    @property
    def _request(self):
        """
        Returns low level method that does not handle authentication but handle
        session initialization.

        Returns:
            requests.Response
        """
        if self._session is None:
            # Lazy import, may never be called
            from requests import Session
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            # Create session with automatic retries on some error codes
            adapter = HTTPAdapter(max_retries=Retry(
                total=self._RETRIES, read=self._RETRIES, connect=self._RETRIES,
                backoff_factor=0.3, status_forcelist=(408, 500, 502, 504)))

            self._session = Session()
            self._session.mount('http://', adapter)
            self._session.mount('https://', adapter)
            self._session_request = self._session.request

        return self._session_request

    def request(self, path, method='get', **kwargs):
        """
        Performs a request with automatic authentication handling.

        Args:
            path (str): URL path
            method (str): Request method.
            kwargs: "Requests.Session.request" keyword arguments.

        Returns:
            dict or list: Response.
        """
        retried = False

        while True:
            # Get authentication token if not already exists
            self._authenticate()

            # Perform request
            response = self._request(
                method, self._endpoint + path, headers={
                    "Authorization": "Bearer " + self._token,
                    "Content-Type": "application/json",
                    "Accept": "application/vnd.accelize.v1+json"},
                timeout=self._TIMEOUT, **kwargs)

            # Authentication token may be invalid, retry with a new one
            if response.status_code == 401 and not retried:
                self._token = ''
                self._token_expire = 0
                retried = True
                continue

            # Handle HTTP status
            elif response.status_code >= 300:
                raise _WebServerException(self._get_error_message(response))

            # Return response content as JSON
            try:
                return response.json()
            except _JSONDecodeError:
                # Some responses return empty content
                return

    @staticmethod
    def _get_error_message(response):
        """
        Return error message from response.

        Args:
            response (requests.Response): Response.

        Returns:
            str: Error message.
        """
        try:
            return response.json()["detail"]
        except (KeyError, _JSONDecodeError):
            return response.text

    def _authenticate(self):
        """
        Authenticate user from its credentials.

        Raises:
            apyfal.exceptions.ClientAuthenticationException:
                User credential are not valid.
        """
        # Check if token expired
        if self._token_expire and self._token_expire < _time():
            self._token = ''

        # Get OAuth2 token
        if not self._token:
            # Get user credentials
            credentials = json_read(get_accelize_cred())
            client_id = credentials['client_id']
            client_secret = credentials['client_secret']

            # Endpoint override in credentials file
            self._endpoint = credentials.get('endpoint', self._ENDPOINT)

            # Try to get CLI cached token
            try:
                self._token, self._token_expire = get_cli_cache(client_id)

            # Try to get token from web service
            except TypeError:
                response = self._request(
                    'post', f'{self._endpoint}/o/token/',
                    data={"grant_type": "client_credentials"},
                    auth=(client_id, client_secret),
                    timeout=self._TIMEOUT)

                if response.status_code >= 300:
                    raise _AuthenticationException(
                        'Unable to authenticate client ID starting by '
                        f'"{client_id[:10]}": '
                        f'{self._get_error_message(response)}')

                access = response.json()
                self._token = access['access_token']
                self._token_expire = int(_time()) + access['expires_in'] - 1

                # Cache token value for future CLI usage
                set_cli_cache(client_id, [self._token, self._token_expire],
                              self._token_expire)


accelize_ws_session = _AccelizeWSSession()

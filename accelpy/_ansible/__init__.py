# coding=utf-8
"""Ansible configuration"""
from os import makedirs, fsdecode, scandir, listdir
from os.path import join, dirname, splitext, isdir
from sys import executable

from accelpy._common import (
    call, get_sources_dirs, symlink, get_sources_filters,
    get_python_package_entry_point, debug, no_color)
from accelpy._yaml import yaml_read, yaml_write


class Ansible:
    """
    Ansible configuration.

    Args:
        config_dir (path-like object): Configuration directory.
    """
    _ANSIBLE_EXECUTABLE = None

    def __init__(self, config_dir):
        self._config_dir = fsdecode(config_dir)

    def create_configuration(self, provider=None, application_type=None,
                             variables=None, user_config=None):
        """
        Generate Ansible configuration.

        Args:
            provider (str): Provider name.
            application_type (str): Application type.
            variables (dict): Ansible playbook variables.
            user_config (path-like object): User configuration directory.
        """
        roles_local = dict()
        yaml_files = dict()

        # Get sources
        for source_dir in get_sources_dirs(dirname(__file__), user_config):
            with scandir(source_dir) as entries:
                for entry in entries:
                    name = entry.name.lower()

                    # Get playbook source
                    if name == 'playbook.yml' and entry.is_file():
                        playbook_src = entry.path

                    # Get roles
                    elif name == 'roles' and entry.is_dir():
                        roles_local.update({role.lower(): join(entry.path, role)
                                            for role in listdir(entry.path)})

                    # Get other Ansible configuration files
                    elif splitext(entry.name)[1] == '.yml':
                        yaml_files[entry.name] = entry.path

        # Filter roles
        roles = {name: path for name, path in roles_local.items()
                 if name.split('.', 1)[0] in get_sources_filters(
                    provider or '', application_type)}

        # Initialize roles
        role_dir = join(self._config_dir, 'roles')
        makedirs(role_dir, exist_ok=True)
        galaxy_roles = set()
        roles_to_init = set(roles)
        initialized_roles = set()

        while roles_to_init:

            role = roles_to_init.pop()
            role_path = roles_local[role]
            initialized_roles.add(role)

            # Link role to configuration directory
            symlink(role_path, join(role_dir, role))

            # Get roles dependencies
            try:
                dependencies = yaml_read(
                    join(role_path, 'meta/main.yml'))['dependencies']
            except (FileNotFoundError, KeyError):
                # No meta in role or no dependencies in meta
                continue

            for dep_entry in dependencies:

                try:
                    # Formatted as "- role: name"
                    dep = dep_entry['role']
                except TypeError:  # pragma: no cover
                    # May also be Formatted as "- name"
                    dep = dep_entry

                # Local dependencies: To initialize
                if dep in roles_local and dep not in initialized_roles:
                    roles_to_init.add(dep)

                # Ansible Galaxy dependencies: To download
                elif dep not in roles_local:
                    galaxy_roles.add(dep)

        # Install dependencies from Ansible Galaxy
        self.galaxy_install(galaxy_roles, roles_path=role_dir)

        # Create playbook
        playbook = yaml_read(playbook_src)
        playbook[0]['vars'] = {
            key: value for key, value in (variables or dict()).items()
            if value is not None}
        roles = sorted(roles)
        playbook[0]['roles'] = (
            [role for role in roles if role.endswith('.init')] +
            [role for role in roles if not role.endswith('.init')])

        yaml_write(playbook, join(self._config_dir, 'playbook.yml'))

        # Copy other configuration files
        for name, path in yaml_files.items():
            symlink(path, join(self._config_dir, name))

    @classmethod
    def _executable(cls):
        """
        Find and return Ansible executable path from this Python environment.

        This ensure to execute a compatible version with the expected Python
        version.

        returns:
            str: path
        """
        if cls._ANSIBLE_EXECUTABLE is None:
            cls._ANSIBLE_EXECUTABLE = get_python_package_entry_point(
                'ansible', 'ansible') or 'ansible'

        return cls._ANSIBLE_EXECUTABLE

    @staticmethod
    def environment():
        """
        Ansible running environment.

        Returns:
            dict: Ansible environment.
        """
        no_color_mode = no_color()
        debug_mode = debug()
        return {
            # Reduce output except in debug mode
            'ANSIBLE_DISPLAY_SKIPPED_HOSTS': debug_mode,
            'ANSIBLE_DISPLAY_OK_HOSTS': debug_mode,
            'ANSIBLE_HOST_KEY_CHECKING': False,
            'ANSIBLE_DEPRECATION_WARNINGS': debug_mode,
            'ANSIBLE_ACTION_WARNINGS': debug_mode,

            # Enable/Disable color outputs (May be useful in some CI env)
            'ANSIBLE_FORCE_COLOR': not no_color_mode,
            'ANSIBLE_NOCOLOR': no_color_mode,

            # Speed up Ansible
            'ANSIBLE_PIPELINING': True,
            'ANSIBLE_SSH_ARGS':
                '"-o ControlMaster=auto -o ControlPersist=60s"'
        }

    def _ansible(self, *args, utility=None, check=True, pipe_stdout=False,
                 **run_kwargs):
        """
        Call Ansible.

        Args:
            args: Ansible positional arguments.
            run_kwargs: subprocess
            check (bool): If True, Check return code for error.
            pipe_stdout (bool): If True, redirect stdout into a pipe, this allow
                to hide outputs from sys.stdout and permit to retrieve stdout as
                "result.stdout".

        Returns:
            subprocess.CompletedProcess: Ansible call result.
        """
        return call(
            [executable, f"{self._executable()}-{utility}" if utility else
             self._executable] + list(arg for arg in args if arg),
            cwd=self._config_dir, check=check, pipe_stdout=pipe_stdout,
            **run_kwargs)

    def galaxy_install(self, roles, roles_path):
        """
        Install role from Ansible galaxy.

        Args:
            roles (iterable of str): Roles to install.
            roles_path (str): Path to the directory containing roles.
        """
        if roles:

            # Lazy import, because may be never used
            from tempfile import TemporaryDirectory
            from concurrent.futures import ThreadPoolExecutor
            from shutil import rmtree, move

            futures = []
            temp_dirs = []
            try:
                # Download roles in parallel to improve speed
                with ThreadPoolExecutor(max_workers=len(roles)) as executor:
                    for role in roles:
                        temp_dir = TemporaryDirectory(dir=roles_path,
                                                      prefix='.accelpy_')
                        temp_dirs.append(temp_dir)
                        futures.append(executor.submit(
                            self._ansible, 'install',
                            f'--roles-path={temp_dir.name}', role,
                            utility='galaxy', pipe_stdout=True, retries=3))

                for future in futures:
                    future.result()

                # Copy roles in target directory
                for temp_dir in temp_dirs:
                    for role in listdir(temp_dir.name):
                        src = join(temp_dir.name, role)
                        dst = join(roles_path, role)
                        if isdir(dst):
                            rmtree(dst, ignore_errors=True)
                        move(src, dst)

            finally:
                for temp_dir in temp_dirs:
                    temp_dir.cleanup()

    @classmethod
    def playbook_exec(cls):
        """
        Ansible playbook command.

        Returns:
            str: command
        """
        return f'{cls._executable()}-playbook'

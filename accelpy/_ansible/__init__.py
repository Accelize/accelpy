# coding=utf-8
"""Ansible configuration"""
from os import makedirs, fsdecode, scandir, listdir
from os.path import join, realpath, dirname, splitext, basename, isfile
from sys import executable

from accelpy._common import (
    yaml_read, yaml_write, call, get_sources_dirs, symlink, get_sources_filters)


class Ansible:
    """
    Ansible configuration.

    Args:
        config_dir (path-like object): Configuration directory.
        provider (str): Provider name.
        application_type (str): Application type.
        variables (dict): Ansible playbook variables.
        user_config (path-like object): User configuration directory.
    """
    _ANSIBLE_EXECUTABLE = None

    def __init__(self, config_dir,
                 provider=None, application_type=None, variables=None,
                 user_config=None):
        self._config_dir = fsdecode(config_dir)
        self._provider = provider or ''
        self._application_type = application_type
        self._variables = variables or dict()
        self._playbook = join(self._config_dir, 'playbook.yml')
        self._source_dirs = get_sources_dirs(dirname(__file__), user_config)
        self._source_names = get_sources_filters(
            self._provider, application_type)

    def create_configuration(self):
        """
        Generate Ansible configuration.
        """
        roles_local = dict()

        # Get sources
        for source_dir in self._source_dirs:
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

        # Filter roles
        roles = {name: path for name, path in roles_local.items()
                 if name.split('.', 1)[0] in self._source_names}

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

                if isinstance(dep_entry, str):
                    # Formatted as "- name"
                    dep = dep_entry
                else:
                    # Formatted as "- role: name"
                    dep = dep_entry['role']

                # Local dependencies: To initialize
                if dep in roles_local and dep not in initialized_roles:
                    roles_to_init.add(dep)

                # Ansible Galaxy dependencies: To download
                elif dep not in roles_local:
                    galaxy_roles.add(dep)

        # Install dependencies from Ansible Galaxy
        self.galaxy_install(galaxy_roles)

        # Create playbook
        playbook = yaml_read(playbook_src)
        playbook[0]['vars'] = {
            key: value for key, value in self._variables.items()
            if value is not None}
        roles = sorted(roles)
        playbook[0]['roles'] = (
            [role for role in roles if role.endswith('.init')] +
            [role for role in roles if not role.endswith('.init')])

        yaml_write(playbook, self._playbook)

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
            from ansible import __path__
            site_packages = dirname(__path__[0])

            # Set default value in case not found
            cls._ANSIBLE_EXECUTABLE = 'ansible"'

            # Tries to find Ansible version installed as dependency
            with scandir(site_packages) as entries:
                for entry in entries:

                    # Find ansible package dist-info
                    if (not entry.name.startswith('ansible-') or
                            splitext(entry.name)[1] != '.dist-info'):
                        continue

                    # Find ansible package files list
                    for name in ('RECORD', 'installed-files.txt'):
                        path = join(entry.path, name)

                        if isfile(path):
                            # Find "ansible" command path
                            with open(path, 'rt') as record:
                                for line in record:
                                    rel_path = line.split(',', 1)[0]
                                    if basename(rel_path) == 'ansible':
                                        cls._ANSIBLE_EXECUTABLE = realpath(join(
                                            site_packages, rel_path))
                                        return cls._ANSIBLE_EXECUTABLE

        return cls._ANSIBLE_EXECUTABLE

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
             self._executable] + list(args), cwd=self._config_dir, check=check,
            pipe_stdout=pipe_stdout, **run_kwargs)

    def lint(self):
        """
        Lint playbook.

        Raises:
            project.exceptions.RuntimeException: Error in playbook.
        """
        self._ansible(self._playbook, '--nocolor', utility='lint',
                      pipe_stdout=True)

    def galaxy_install(self, roles):
        """
        Install role from Ansible galaxy.

        Args:
            roles (iterable of str): Roles to install.
        """
        if roles:
            self._ansible('install', *roles, utility='galaxy')

    @classmethod
    def playbook_exec(cls):
        """
        Ansible playbook command.

        Returns:
            str: command
        """
        return f'{cls._executable()}-playbook'

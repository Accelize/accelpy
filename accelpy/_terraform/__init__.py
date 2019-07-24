# coding=utf-8
"""Terraform configuration"""
from json import loads
from os import makedirs, remove
from os.path import join, isfile
from time import sleep

from accelpy._common import json_write, symlink, no_color
from accelpy._hashicorp import Utility
from accelpy.exceptions import RuntimeException


class Terraform(Utility):
    """Terraform configuration.

    Configuration is built using sources Terraform configurations files found
    from:

    - Default configuration.
    - User home directory.
    - Current working directory.
    - Directory specified by "user_config" argument.

    If multiples files with the same name are found, the last one found is used.
    Directories are checked in the listed order to allow user to override
    default configuration easily.

    Args:
        config_dir (path-like object): Configuration directory.
        provider (str): Provider name.
            Required only if no "host_id" provided.
        user_config (path-like object): User configuration directory.
            Required only if no "host_id" provided.
        variables (dict): Terraform input variables.
            Required only if no "host_id" provided.
    """
    _executable = None
    _FILE = __file__
    _EXTS_INCLUDE = ('.tf', '.tfvars', '.tf.json', '.tfvars.json')

    def __init__(self, *args, **kwargs):
        Utility.__init__(self, *args, **kwargs)
        self._initialized = False

    def create_configuration(self):
        """
        Generate Terraform configuration.

        Configuration is built using sources Terraform configurations files
        found from:

        - This module provided default configuration.
        - Configuration from user home directory.
        - Current working directory.
        - Directory specified by "user_config" argument.

        If multiples files with the same name are found, the last one found is
        used. Directories are checked in the listed order to allow user to
        override default configuration easily.
        """
        # Symlink common plugins dir to to avoid to re-download them each time
        dot_dir = join(self._config_dir, '.terraform')
        makedirs(dot_dir, exist_ok=True)
        symlink(self._plugins_dir(), join(dot_dir, 'plugins'))
        # Link configuration files matching provider and options
        for name, src_path in self._list_sources():
            dst_path = join(self._config_dir, name)

            # Replace existing file
            try:
                remove(dst_path)
            except OSError:
                pass

            # Create symbolic link to configuration file
            symlink(src_path, dst_path)

        # Add variables
        tf_vars = {
            key: value for key, value in self._variables.items()
            if value is not None}
        json_write(
            tf_vars, join(self._config_dir, 'generated.auto.tfvars.json'))

    @property
    def _no_color(self):
        """
        Configure color.

        Returns:
            str: color argument.
        """
        return '-no-color' if no_color() else ''

        # Initialize terraform
    def _init(self):
        """
        Initialize Terraform
        """
        if not self._initialized:
            self._exec('init', self._no_color, '-input=false', pipe_stdout=True)
            self._initialized = True

    def plan(self):
        """
        Generate and show an execution plan. a TF plan is also saved in the
        configuration directory.

        Returns:
            str: Command output
        """
        self._init()
        return self._exec('plan', self._no_color, '-input=false', '-out=tfplan',
                          pipe_stdout=True).stdout

    def apply(self, quiet=False, retries=10, delay=1.0):
        """
        Builds or changes infrastructure.

        Args:
            quiet (bool): If True, hide outputs.
            retries (int): Number of time to retries to apply the configuration.
                Apply is retried only on a specified set of known retryable
                errors.
            delay (float): Delay to wait between retries
        """
        self._init()

        failures = 0
        args = ['apply', self._no_color, '-auto-approve', '-input=false']
        if isfile(join(self._config_dir, 'tfplan')):
            # Use "tfplan" if any
            args.append('tfplan')

        while True:
            try:
                self._exec(*args, pipe_stdout=quiet)
                break
            except RuntimeException as exception:
                if failures > retries:
                    raise RuntimeException(
                        f'Unable to apply after {retries} retries\n\n'
                        f'{str(exception)}')

                for retryable_error in (
                        "Error requesting spot instances: "
                        "InvalidSubnetID.NotFound: "
                        "No default subnet for availability zone: 'null'",
                        'Error while waiting for spot request',):
                    if retryable_error in str(exception):
                        break
                else:
                    raise
                failures += 1
                sleep(delay)

    def destroy(self, quiet=False):
        """
        Destroy Terraform-managed infrastructure.

        Args:
            quiet (bool): If True, hide outputs.
        """
        self._init()
        self._exec('destroy', self._no_color, '-auto-approve',
                   pipe_stdout=quiet)

    def refresh(self, quiet=False):
        """
        Reconcile the state Terraform knows about with the
        real-world infrastructure

        Args:
            quiet (bool): If True, hide outputs.
        """
        if self._has_state():
            self._init()
            self._exec('refresh', self._no_color, '-input=false', '.',
                       pipe_stdout=quiet)

    @property
    def output(self):
        """
        Read outputs from the Terraform state.

        Returns:
            dict: Configuration output.
        """
        process = self._exec('output', self._no_color, '-json',
                             pipe_stdout=True)
        out = loads(process.stdout.strip())
        return {key: out[key]['value'] for key in out}

    def state_list(self):
        """
         list resources within the Terraform state.

        Returns:
            list of str: List of resources.
        """
        result = self._exec('state', 'list', pipe_stdout=True, check=False)

        if result.returncode:
            # Error because no state file, return empty list
            if not self._has_state():
                return []

            # Other errors: Raise
            raise RuntimeException(result.stderr)

        # No errors, return state
        return result.stdout.strip().splitlines()

    def _has_state(self):
        """
        Check if Terraform has state file.

        Returns:
            bool: True if Terraform state present.
        """
        return isfile(join(self._config_dir, 'terraform.tfstate'))

"""Manage hosts life-cycle"""
from os import chmod, fsdecode, makedirs, scandir, symlink
from os.path import isabs, isdir, isfile, join, realpath

from accelpy._application import Application
from accelpy._common import (
    HOME_DIR, json_read, json_write, get_sources_dirs, no_color, debug)
from accelpy.exceptions import ConfigurationException

CONFIG_DIR = join(HOME_DIR, 'hosts')


def iter_hosts():
    """
    Iter over existing hosts configurations.

    Returns:
        generator of accelpy._manager.Host: Generator of Host
        configurations.
    """
    for entry in scandir(CONFIG_DIR):
        if entry.is_dir():
            yield Host(name=entry.name)


class Host:
    """Host configuration.

    Args:
        name (str): Name of the host or virtual machine image.
            If an host with this name already exists,
            its configuration will be loaded, else a new configuration will be
            created. If not specified, a random name will be generated.
        application (path-like object): Path to application definition file.
            Required only to create a new configuration.
        provider (str): Provider name.
            Required only to create a new configuration.
        user_config (path-like object): User configuration directory.
            Always also use the "~./accelize" directory.
            Required only to create a new configuration.
        destroy_on_exit (bool): If True, automatically destroy the
            Terraform-managed infrastructure on exit.
        keep_config (bool): If True, does not remove configuration on context
            manager exit or object deletion. A configuration is never removed if
            its Terraform managed infrastructure still exists
    """
    def __init__(self, name=None, application=None, provider=None,
                 user_config=None, destroy_on_exit=False,
                 keep_config=True):

        # Initialize some futures values
        self._ansible_config = None
        self._packer_config = None
        self._terraform_config = None
        self._terraform_output = None
        self._application_definition = None

        # If true, Terraform infrastructure is destroyed on exit
        self._destroy_on_exit = destroy_on_exit
        self._keep_config = keep_config

        # Define name
        if not name:
            from uuid import uuid1
            name = str(uuid1()).replace('-', '')
        self._name = name

        # Define configuration directory en files
        self._config_dir = join(CONFIG_DIR, name)
        user_parameters_json = join(self._config_dir, 'user_parameters.json')
        self._output_json = join(self._config_dir, 'output.json')
        self._accelize_drm_conf_json = join(
            self._config_dir, 'accelize_drm_conf.json')
        self._accelize_drm_cred_json = join(self._config_dir, 'cred.json')

        # Create a new configuration
        config_exists = isdir(self._config_dir)
        if not config_exists and application:

            # Ensure config is cleaned on creation error
            self._keep_config = False

            # Create target configuration directory and remove access to other
            # users since Terraform state files may content sensible data and
            # directory may contain SSH private key
            makedirs(self._config_dir, exist_ok=True)
            chmod(self._config_dir, 0o700)

            # Get user parameters used
            self._provider = provider
            self._user_config = fsdecode(user_config or HOME_DIR)

            # Save user parameters
            json_write(dict(provider=self._provider,
                            user_config=self._user_config),
                       user_parameters_json)

            # Get application and add it as link with configuration
            self._application_yaml = realpath(fsdecode(application))

            # Check Accelize Requirements
            self._init_accelize_drm()

            # Add link to configuration
            symlink(self._application_yaml, join(
                self._config_dir, 'application.yml'))

            # Initialize Terraform and Ansible configuration
            self._terraform.create_configuration()
            self._ansible.create_configuration()
            self._packer.create_configuration()

            self._keep_config = keep_config

        # Load an existing configuration
        elif config_exists:

            # Retrieve application parameters
            self._application_yaml = realpath(join(
                self._config_dir, 'application.yml'))

            # Retrieve user parameters
            user_parameters = json_read(user_parameters_json)
            self._provider = user_parameters['provider']
            self._user_config = user_parameters['user_config']

        # Unable to create configuration
        else:
            raise ConfigurationException(
                'Require at least an existing host name, or an '
                'application to create a new host.')

    def _init_accelize_drm(self):
        """Initialize Accelize DRM requirements"""

        # Create configuration file from application
        accelize_drm_enable = self._app('accelize_drm', 'use_service')
        accelize_drm_conf = self._app('accelize_drm', 'conf')

        if accelize_drm_enable and not accelize_drm_conf:
            raise ConfigurationException(
                'Application definition section "accelize_drm" require '
                '"conf" value to be specified if "use_service" is '
                'specified.')

        json_write(accelize_drm_conf, self._accelize_drm_conf_json)

        # Get credentials file from user configuration
        for src in get_sources_dirs(self._user_config):

            cred_path = join(src, 'cred.json')

            if isfile(cred_path):
                symlink(cred_path, self._accelize_drm_cred_json)
                break
        else:
            raise ConfigurationException(
                'No Accelize DRM credential found. Please, make sure to '
                f'have your "cred.json" file installed in "{HOME_DIR}", '
                f'current directory or path specified with the '
                f'"user_config" argument.')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._clean_up()

    def __del__(self):
        self._clean_up()

    def __str__(self):
        return f'<{self.__class__.__module__}.{self.__class__.__name__} ' \
            f'(name={self._name})>'

    def __repr__(self):
        return self.__str__()

    def plan(self):
        """
        Plan the host infrastructure creation and show details.

        Returns:
            str: Show planned infrastructure detail.
        """
        return self._terraform.plan()

    def apply(self, quiet=False):
        """
        Create the host infrastructure.

        Args:
            quiet (bool): If True, hide outputs.
        """
        # Reset cached output
        self._terraform_output = None

        # Apply
        self._terraform.apply(quiet=quiet)

    def build(self, update_application=False, quiet=False):
        """
        Create a virtual machine image of the configured host.

        Args:
            update_application (bool): If applicable, update the application
                definition Yaml file to use this image as host base for the
                selected provider. Warning, this will reset any yaml file
                formatting and comments.
            quiet (bool): If True, hide outputs.

        Returns:
            str: Image ID or path (Depending provider)
        """
        manifest = self._packer.build(quiet=quiet)
        image = self._packer.get_artifact(manifest)

        if update_application and self._application_yaml:
            application = Application(self._application_yaml)
            try:
                section = application['package'][self._provider]
            except KeyError:
                section = application['package'][self._provider] = dict()

            section['type'] = 'vm_image'
            section['name'] = image
            application.save()

        return image

    def destroy(self, quiet=False, delete=None):
        """
        Destroy the host infrastructure.

        Args:
            quiet (bool): If True, hide outputs.
            delete (bool): If True, also delete the configuration on context
                manager exit or object deletion.
        """
        if delete is not None:
            self._keep_config = not delete
        self._terraform.destroy(quiet=quiet)
        self._terraform_output = None

    @property
    def ssh_private_key(self):
        """
        Host SSH private key.

        Returns:
            str: Path ro Private key to use to connect to host using SSH.
        """
        path = self._get_terraform_output('host_ssh_private_key')
        return (path if isabs(path) else
                # Terraform returns relative path as "./file"
                join(self._config_dir, path.lstrip('./')))

    @property
    def ssh_user(self):
        """
        Name of the user to use to connect with SSH.

        Returns:
            str: User name.
        """
        return self._get_terraform_output('remote_user')

    @property
    def name(self):
        """
        Name of the host or the image.

        Returns:
            str: Name.
        """
        return self._name

    @property
    def private_ip(self):
        """
        Private IP address.

        Returns:
            str: IP address.
        """
        return self._get_terraform_output('host_private_ip')

    @property
    def public_ip(self):
        """
        Public IP address.

        Returns:
            str: IP address.
        """
        return self._get_terraform_output('host_public_ip')

    def _app(self, section, key):
        """
        Get application value for specified provider

        Args:
            section (str): Definition section.
            key (str): Definition key.

        Returns:
            Value
        """
        return self._application.get(section, key, env=self._provider)

    def _get_terraform_output(self, key):
        """
        Get an output from Terraform state.

        Args:
            key (str):

        Returns:
            str: Output result
        """
        if not self._terraform_output:
            # Load and cache Terraform outputs
            self._terraform_output = self._terraform.output

        try:
            return self._terraform_output[key]
        except KeyError:
            raise ConfigurationException('Configuration not applied.')

    @property
    def _ansible(self):
        """
        Ansible utility.

        Returns:
            project._ansible.Ansible: Ansible
        """
        if not self._ansible_config:
            # Lazy import: May not be used all time
            from accelpy._ansible import Ansible

            # Set Ansible variables
            variables = dict(
                fpga_image=self._app('fpga', 'image'),
                fpga_driver=self._app('fpga', 'driver'),
                fpga_driver_version=self._app('fpga', 'driver_version'),
                fpga_slots=[
                    slot for slot in range(int(self._app('fpga', 'count')))],
                firewall_rules=self._application['firewall_rules'],
                package_name=self._app('package', 'name'),
                package_version=self._app('package', 'version'),
                package_repository=self._app('package', 'repository'),
                accelize_drm_disabled=not self._app('accelize_drm',
                                                    'use_service'),
                accelize_drm_conf_src=self._accelize_drm_conf_json,
                accelize_drm_cred_src=self._accelize_drm_cred_json
            )
            variables.update(self._app('application', 'variables'))

            self._ansible_config = Ansible(
                config_dir=self._config_dir, provider=self._provider,
                application_type=self._app('application', 'type'),
                variables=variables)

        return self._ansible_config

    @property
    def _packer(self):
        """
        Packer utility.

        Returns:
            project._packer.Packer: Packer
        """
        if not self._packer_config:
            # Lazy import: May not be used all time
            from accelpy._packer import Packer
            from accelpy._ansible import Ansible

            variables = {
                f'provider_param_{index}': value
                for index, value in enumerate(
                    (self._provider or '').split(','))}
            variables['image_name'] = self._name
            variables['ansible'] = Ansible.playbook_exec()

            self._packer_config = Packer(
                provider=self._provider, config_dir=self._config_dir,
                user_config=self._user_config, variables=variables)

        return self._packer_config

    @property
    def _terraform(self):
        """
        Terraform utility.

        Returns:
            project._terraform.Terraform: Terraform
        """
        if not self._terraform_config:
            # Lazy import: May not be used all time
            from accelpy._terraform import Terraform
            from accelpy._ansible import Ansible

            no_color_mode = no_color()
            debug_mode = debug()
            ansible_env = ' '.join(f'{key}={value}' for key, value in {
                'ANSIBLE_DISPLAY_SKIPPED_HOSTS': debug_mode,
                'ANSIBLE_DISPLAY_OK_HOSTS': debug_mode,
                'ANSIBLE_HOST_KEY_CHECKING': False,
                'ANSIBLE_DEPRECATION_WARNINGS': debug_mode,
                'ANSIBLE_ACTION_WARNINGS': debug_mode,
                'ANSIBLE_FORCE_COLOR': not no_color_mode,
                'ANSIBLE_NOCOLOR': no_color_mode
            }.items())

            variables = dict(
                ansible=f"{ansible_env} {Ansible.playbook_exec()}",
                firewall_rules=self._application['firewall_rules'],
                fpga_count=self._app('fpga', 'count'),
                package_vm_image=self._app('package', 'name')
                if self._app('package', 'type') == 'vm_image' else '',
                host_name=self._name,
                host_provider=self._provider
            )

            self._terraform_config = Terraform(
                provider=self._provider, config_dir=self._config_dir,
                user_config=self._user_config, variables=variables)

        return self._terraform_config

    @property
    def _application(self):
        """
        Application definition.

        Returns:
            accelpy._application.Application: Definition
        """
        if not self._application_definition:
            self._application_definition = Application(self._application_yaml)

        return self._application_definition

    def _terraform_has_state(self):
        """
        Check if Terraform has a state.

        Returns:
            bool: True If Terraform has state.
        """
        try:
            return bool(self._terraform.state_list())
        except (ConfigurationException, FileNotFoundError):
            return False

    def _clean_up(self):
        """
        Clean up configuration directory if there is no remaining resource
        within the Terraform state.
        """
        if self._config_dir is not None and isdir(self._config_dir):
            # Destroy managed infrastructure if exists
            if self._destroy_on_exit and self._terraform_has_state():
                self._terraform.destroy(quiet=True)

            # Check if there is some remaining resources in state file
            # If it is the case, do not clean up configuration to allow
            # to reuse it
            if not self._terraform_has_state() and not self._keep_config:

                # Lazy import: Only used on remove
                from shutil import rmtree

                rmtree(self._config_dir, ignore_errors=True)

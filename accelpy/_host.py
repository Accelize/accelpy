"""Manage hosts life-cycle"""
from os import chmod, fsdecode, makedirs, scandir, symlink
from os.path import isabs, isdir, isfile, join, realpath

from accelpy._common import HOME_DIR, get_accelize_cred, json_read, json_write
from accelpy.exceptions import ConfigurationException, AccelizeException

CONFIG_DIR = join(HOME_DIR, 'hosts')


def _iter_hosts_names():
    """
    Iter over existing hosts configurations names.

    Returns:
        generator of str: Generator of host configuration names.
    """
    try:
        for entry in scandir(CONFIG_DIR):
            if entry.is_dir():
                yield entry.name
    except OSError:
        return


def iter_hosts():
    """
    Iter over existing hosts configurations.

    Returns:
        generator of accelpy._manager.Host: Generator of Host
        configurations.
    """
    for name in _iter_hosts_names():
        yield Host(name=name)


class Host:
    """Host configuration.

    Args:
        name (str): Name of the host or virtual machine image.
            If an host with this name already exists,
            its configuration will be loaded, else a new configuration will be
            created. If not specified, a random name will be generated.
        application (str or path-like object): Application in format
            "product_id:version" (or "product_id" for latest version) or
            path to a local application definition file.
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
                 user_config=None, destroy_on_exit=False, keep_config=True):

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
            # Lazy import: May not be used all time
            from uuid import uuid1

            name = str(uuid1()).replace('-', '')
        self._name = name

        # Define configuration directory en files
        self._config_dir = join(CONFIG_DIR, name)
        config_exists = isdir(self._config_dir)

        self._user_parameters_json = join(
            self._config_dir, 'user_parameters.json')

        # Create a new configuration

        if not config_exists and application:
            self._create_config(application, provider, user_config)

        # Unable to create configuration
        elif not config_exists:
            raise ConfigurationException(
                'Require at least an existing host name, or an '
                'application to create a new host.')

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

    def _create_config(self, application, provider, user_config):
        """
        Create configuration.

        Args:
            application (str or path-like object):
                Application or path to application definition file.
            provider (str): Provider name.
            user_config (path-like object): User configuration directory.
        """
        # Ensure config is cleaned on creation error
        keep_config = self._keep_config
        self._keep_config = False

        # Create target configuration directory and remove access to other
        # users since Terraform state files may content sensible data and
        # directory may contain SSH private key
        makedirs(self._config_dir, exist_ok=True)
        chmod(self._config_dir, 0o700)

        # Save user parameters
        user_config = fsdecode(user_config or HOME_DIR)
        json_write(dict(provider=provider, user_config=user_config),
                   self._user_parameters_json)

        # Get application and its definition
        self._init_application_definition(application)

        def app(section, key):
            """
            Get application value for specified provider

            Args:
                section (str): Definition section.
                key (str): Definition key.

            Returns:
                Value
            """
            return self._application.get(section, key, env=provider)

        fpga_count = app('fpga', 'count')
        package_name = app('package', 'name')
        application_type = app('application', 'type')
        accelize_drm_enable = app('accelize_drm', 'use_service')
        name = self._name

        # Check Accelize DRM Requirements
        accelize_drm_cred_json = self._init_accelize_cred(user_config)
        accelize_drm_conf_json = self._init_accelize_conf(
            app('accelize_drm', 'conf'), accelize_drm_enable, provider)

        # Lazy import, because may not be always used
        from concurrent.futures import ThreadPoolExecutor
        from accelpy._ansible import Ansible

        # Set Ansible variables
        ansible_env = Ansible.environment()
        ansible_exec = Ansible.playbook_exec()
        ansible_variables = dict(
            fpga_image=app('fpga', 'image'),
            fpga_driver=app('fpga', 'driver'),
            fpga_driver_version=app('fpga', 'driver_version'),
            fpga_slots=[slot for slot in range(fpga_count)],
            firewall_rules=self._application['firewall_rules'],
            package_name=package_name,
            package_version=app('package', 'version'),
            package_repository=app('package', 'repository'),
            accelize_drm_disabled=not accelize_drm_enable,
            accelize_drm_conf_src=accelize_drm_conf_json,
            accelize_drm_cred_src=accelize_drm_cred_json
        )
        ansible_variables.update(app('application', 'variables'))

        # Set Packer variables
        packer_variables = {
            f'provider_param_{index}': value
            for index, value in enumerate((provider or '').split(','))}
        packer_variables.update(dict(
            image_name=name,
            ansible=ansible_exec,
            fpga_count=str(fpga_count)
        ))

        # Set Terraform variables
        terraform_variables = dict(
            ansible=' '.join(
                [f'{key}={value}' for key, value in ansible_env.items()] +
                [ansible_exec]),
            firewall_rules=self._application['firewall_rules'],
            fpga_count=fpga_count,
            package_vm_image=package_name if app(
                'package', 'type') == 'vm_image' else '',
            host_name=name,
            host_provider=provider
        )

        # Initialize utilities configuration
        futures = []
        with ThreadPoolExecutor(max_workers=3) as executor:

            for utility, variables in (
                    (self._terraform, terraform_variables),
                    (self._ansible, ansible_variables),
                    (self._packer, packer_variables)):

                futures.append(executor.submit(
                    getattr(utility, 'create_configuration'),
                    provider=provider, application_type=application_type,
                    variables=variables, user_config=user_config))

        for future in futures:
            future.result()

        # Restore keep config flag once configuration si completed
        self._keep_config = keep_config

    def _init_accelize_cred(self, user_config):
        """
        Initialize Accelize Credentials.

        Args:
            user_config (str): Path to user configuration directory

        Returns:
            str: Path to cred.json
        """
        accelize_drm_cred_json = join(self._config_dir, 'cred.json')
        symlink(get_accelize_cred(user_config), accelize_drm_cred_json)
        return accelize_drm_cred_json

    def _init_accelize_conf(self,
                            accelize_drm_conf, accelize_drm_enable, provider):
        """
        Initialize Accelize DRM Configuration.

        Args:
            accelize_drm_conf (dict): conf.json content
            accelize_drm_enable (bool): True if service is enabled
            provider (str): Provider.

        Returns:
            str: Path to conf.json
        """
        # Create configuration file from application
        if accelize_drm_enable and not accelize_drm_conf:
            raise ConfigurationException(
                'Application definition section "accelize_drm" require '
                '"conf" value to be specified if "use_service" is '
                'specified.')

        accelize_drm_conf_json = join(
            self._config_dir, 'accelize_drm_conf.json')

        if provider:
            # Set board type value to provider
            try:
                design = accelize_drm_conf['design']
            except KeyError:
                accelize_drm_conf['design'] = design = dict()
            design['boardType'] = provider

        json_write(accelize_drm_conf, accelize_drm_conf_json)

        return accelize_drm_conf_json

    def _init_application_definition(self, application):
        """
        Get remote or local application definition and save it locally.

        Args:
            application (str or path-like object):
                Application or path to application definition file.
        """
        dst_path = join(self._config_dir, 'application.yml')

        # Try if application is a local path
        src_path = realpath(fsdecode(application))

        # Link local definition file in configuration directory
        if isfile(src_path):
            return symlink(src_path, dst_path)

        # Lazy import: May not be used all time
        from accelpy._application import Application

        # Get application definition from accelize server
        Application.from_id(application).save(dst_path)

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

        if update_application:
            provider = json_read(self._user_parameters_json)['provider']
            try:
                section = self._application['package'][provider]
            except KeyError:
                section = self._application['package'][provider] = dict()

            section['type'] = 'vm_image'
            section['name'] = image
            self._application.save()

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

            self._ansible_config = Ansible(config_dir=self._config_dir)

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

            self._packer_config = Packer(config_dir=self._config_dir)

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

            self._terraform_config = Terraform(config_dir=self._config_dir)

        return self._terraform_config

    @property
    def _application(self):
        """
        Application definition.

        Returns:
            accelpy._application.Application: Definition
        """
        if not self._application_definition:
            # Lazy import: May not be used all time
            from accelpy._application import Application

            self._application_definition = Application(realpath(join(
                self._config_dir, 'application.yml')))

        return self._application_definition

    def _terraform_has_state(self):
        """
        Check if Terraform has a state.

        Returns:
            bool: True If Terraform has state.
        """
        try:
            return bool(self._terraform.state_list())
        except (AccelizeException, FileNotFoundError):
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

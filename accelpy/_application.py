# coding=utf-8
"""Application Definition"""
from os import fsdecode

from accelpy._common import yaml_read, yaml_write
from accelpy.exceptions import ConfigurationException

# Application definition format
FORMAT = {
    'application': {
        '_node': dict,
        'name': dict(
            required=True,
            desc='Application name'),
        'version': dict(
            required=True,
            desc='Application version'),
        'type': dict(
            required=True,
            desc='Application type.',
            values=('container_service', 'kubernetes_node'),
            default='container_service'),
        'variables': dict(
            desc='Application variables. See application type documentation to '
                 'see available variables.',
            value_type=dict,
            default={},
        )
    },
    'package': {
        '_node': dict,
        'type': dict(
            default='container_image',
            values=('container_image', 'vm_image'),
            desc='Type of package.'),
        'name': dict(
            required=True,
            desc='Package name or ID'),
        'version': dict(
            desc='Package version. Latest available if not specified'),
        'repository': dict(
            desc='Package repository. Only required if using a non standard '
                 'repository'),
    },
    'firewall_rules': {
        '_node': list,
        'start_port': dict(
            required=True,
            value_type=int,
            desc='Start of port range to allow.'),
        'end_port': dict(
            required=True,
            value_type=int,
            desc='End of port range to allow.'),
        'protocol': dict(
            values=('tcp', 'udp', 'all'),
            default='tcp',
            desc='Protocol to allow.'),
        'direction': dict(
            values=('ingress', 'egress'),
            default='ingress',
            desc='Direction to allow.'),
    },
    'fpga': {
        '_node': dict,
        'image': dict(
            required=True,
            value_type=(list, str),
            desc='FPGA bitstream image to use. Should be a single string or a '
                 'list of strings with same number of elements as FPGA count.'
        ),
        'driver': dict(
            desc='FPGA driver to use, default to Linux kernel driver.',
            values=('aws_f1', 'xilinx_xrt')),
        'driver_version': dict(
            desc='FPGA driver version to use. If not specified, '
                 'use latest available.'
        ),
        'count': dict(
            default=1,
            value_type=int,
            desc='Number of FPGA devices required to run the application.'
        )
    },
    'accelize_drm': {
        '_node': dict,
        'use_service': dict(
            value_type=bool,
            default=True,
            desc='Use the Accelize DRM service to handle Accelize DRM. If not '
                 'enabled, the application must handle the DRM itself using '
                 'the Accelize DRM library.'
        ),
        'conf': dict(
            desc='Accelize DRM configuration.',
            value_type=dict,
            default={},
        ),
    },
    'test': {
        '_node': dict,
        'shell': dict(
            desc='Shell command used to test application that should return a 0'
                 ' code in cas of success.'
        )
    }
}


def lint(path):
    """
    Validate an application definition file.

    Args:
        path (path-like object): Path to yaml definition file.

    Raises:
        accelpy.exceptions.ConfigurationException: Error in definition
        file.
    """
    Application(path)


class Application:
    """
    Application definition

    Args:
        definition_file (path-like object): Path to yaml definition file.
    """

    def __init__(self, definition_file):
        self._path = fsdecode(definition_file)
        self._environments = set()
        self._definition = self._validate(yaml_read(self._path))

    def __getitem__(self, key):
        return self._definition.__getitem__(key)

    @property
    def environments(self):
        """
        Environments specified in definition.

        Returns:
            set of str: Environments
        """
        return self._environments

    def get(self, section, key, env=None):
        """
        Return value from definition.

        Args:
            section (str): Definition section.
            key (str): Definition key.
            env (str): Environment. None for use default environment value.

        Returns:
            Value
        """
        # Return specific environment value
        try:
            return self._definition[section][env][key]

        # Return default environment value
        except KeyError:
            return self._definition[section][key]

    def save(self, path=None):
        """
        Save the definition file.

        Args:
            path (path-like object): Path where save Yaml definition file.
        """
        yaml_write(self._definition, path or self._path)

    def _validate(self, definition):
        """
        Validate definition file content, and complete missing values.

        Args:
            definition (dict): Definition.

        Returns:
            dict: definition

        Raises:
            ValueError: Error in section format.
        """
        for section_name in FORMAT:

            section_format = FORMAT[section_name]
            node_type = section_format['_node']

            try:
                section = definition[section_name]
            except KeyError:
                # Create missing definition section
                section = definition[section_name] = node_type()

            self._validate_section(
                node_type, section, section_name, section_format)

        # Check for unknown sections
        for section_name in definition:
            if section_name not in FORMAT:
                raise ConfigurationException(
                    f'Unknown "{section_name}" section.')

        return definition

    def _validate_section(
            self, node_type, section, section_name, section_format):
        """
        Validate a section

        Args:
            node_type (class): Type of node (dict or list)
            section (dict or list): Section to validate.
            section_name (str): Section name.
            section_format (dict): Section format.

        Raises:
            ValueError: Error in section format.
        """
        if not isinstance(section, node_type):
            raise ConfigurationException(
                f'The section "{section_name}" must be a '
                f'{"mapping" if node_type == dict else "list"}.')

        for node in (section if isinstance(section, list) else (section,)):
            args = (node, section_format, section_name)
            self._validate_node(*args)
            if not self._validate_env_node(*args):
                self._check_required(*args)

    @staticmethod
    def _validate_node(node, node_format, section_name):
        """
        Validate a node.

        Args:
            node (dict): Node to validate
            node_format (dict): Node format
            section_name (str): Parent section name.

        Raises:
            accelpy.exceptions.ConfigException: Error in node format.
        """
        for key in node_format:

            if key == '_node':
                continue

            key_format = node_format[key]

            # Set default value if missing
            node.setdefault(key, key_format.get('default'))
            value = node[key]

            # Check and eventually update value
            node[key] = Application._check_value(
                key, key_format, value, section_name)

    @staticmethod
    def _check_required(node, node_format, section_name):
        """
        Check for required value in default env.

        Args:
            node (dict): Node to validate
            node_format (dict): Node format
            section_name (str): Parent section name.

        Raises:
            accelpy.exceptions.ConfigException: Error in node format.
        """
        for key in node_format:

            if key == '_node':
                continue

            # Check required value for default environment
            if node_format[key].get('required', False) and node[key] is None:
                raise ConfigurationException(
                    f'The "{key}" key in "{section_name}" section is required.')

    @staticmethod
    def _check_value(key, key_format, value, section_name):
        """
        Check if value is valid

        Args:
            key (str): Key
            key_format (dict): Key format
            value: Key value
            section_name (str): Section name

        Returns:
            value.

        Raises:
            accelpy.exceptions.ConfigException: Error in value.
        """
        valid_values = key_format.get('values')
        if valid_values and not (
                value in valid_values or value == key_format.get('default')):
            raise ConfigurationException(
                f'Invalid value "{value}" for "{key}" key in "{section_name}" '
                f'section (possibles values are '
                f'{", ".join(str(valid_value) for valid_value in valid_values)}'
                ').')

        value_type = key_format.get('value_type', str)
        if isinstance(value_type, tuple) and value_type[0] == list:
            # Checks value content type
            if isinstance(value, value_type[0]):
                for element in value:
                    if not isinstance(element, value_type[1]):
                        raise ConfigurationException(
                            f'The "{key}" key in "{section_name}" section must '
                            f'be a list of "{value_type[1].__name__}".')

            # Single element list
            elif isinstance(value, value_type[1]):
                return [value]

            # Bad value
            elif value is not None:
                raise ConfigurationException(
                    f'The "{key}" key in "{section_name}" section must be a '
                    f'list of "{value_type[1].__name__}".')

        elif value is not None and not isinstance(value, value_type):
            raise ConfigurationException(
                f'The "{key}" key in "{section_name}" section must be a '
                f'"{value_type.__name__}".')

        return value

    def _validate_env_node(self, node, node_format, section_name):
        """
        Validate an environment override node.

        Args:
            node (dict): Node to validate
            node_format (dict): Node format
            section_name (str): Parent section name.

        Raises:
            ValueError: Error in node format.

        Returns:
            bool: True in at least one env found.
        """
        env_found = False
        for env in node:

            # Not an env
            if env in node_format:
                continue

            # Env found
            self._environments.add(env)
            env_found = True
            env_node = node[env]

            # Env that is not a dict is likely an unknown key
            if not isinstance(env_node, dict) or env_node == '_node':
                raise ConfigurationException(
                    f'Unknown "{env_node}" key in "{section_name}" section.')

            # Check environment integrity
            for key in node_format:

                if key == '_node':
                    continue

                value = env_node.get(key, node.get(key))
                key_format = node_format[key]

                # Required value for environment
                if key_format.get('required', False) and value is None:
                    raise ConfigurationException(
                        f'The "{key}" key in "{section_name}" section is '
                        f'required for "{env}" environment.')

                # Check value
                if key in env_node:
                    env_node[key] = Application._check_value(
                        key, key_format, value, section_name)

            # Check for unknown keys in environment
            for key in env_node:
                if key not in node_format or key == '_node':
                    raise ConfigurationException(
                        f'Unknown "{key}" key in "{section_name}" section '
                        f'for "{env}" environment.')

        return env_found

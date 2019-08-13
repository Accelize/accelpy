# coding=utf-8
"""Application Definition"""
from os import fsdecode
from re import fullmatch

from accelpy._common import request
from accelpy._yaml import yaml_read, yaml_write
from accelpy.exceptions import ConfigurationException

# Application definition format
FORMAT = {
    'application': {
        '_node': dict,
        'product_id': dict(
            required=True),
        'version': dict(
            required=True,
            regex_help='The version must be in semantic versioning format',
            regex=r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)'
                  r'(-(0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)'
                  r'(\.(0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*)?'
                  r'(\+[0-9a-zA-Z-]+(\.[0-9a-zA-Z-]+)*)?$'),
        'type': dict(
            required=True,
            values=('container_service', 'kubernetes_node'),
            default='container_service'),
        'variables': dict(
            value_type=dict,
            default={})
    },
    'package': {
        '_node': list,
        'type': dict(
            default='container_image',
            values=('container_image', 'vm_image', 'kubernetes_yaml')),
        'name': dict(
            required=True,),
        'version': dict(),
        'repository': dict(),
    },
    'firewall_rules': {
        '_node': list,
        'start_port': dict(
            required=True,
            value_type=int),
        'end_port': dict(
            required=True,
            value_type=int),
        'protocol': dict(
            values=('tcp', 'udp', 'all'),
            default='tcp'),
        'direction': dict(
            values=('ingress', 'egress'),
            default='ingress'),
    },
    'fpga': {
        '_node': dict,
        'image': dict(
            required=True,
            value_type=(list, str)),
        'driver': dict(
            values=('aws_f1', 'xilinx_xrt')),
        'driver_version': dict(),
        'count': dict(
            default=1,
            value_type=int)
    },
    'accelize_drm': {
        '_node': dict,
        'use_service': dict(
            value_type=bool,
            default=True),
        'conf': dict(
            value_type=dict,
            default={}),
    },
    'test': {
        '_node': dict,
        'shell': dict()
    }
}


class Application:
    """
    Application definition

    Args:
        definition (path-like object or dict):
            Path to yaml definition file or dict of the content of the
            definition.
    """

    def __init__(self, definition):
        self._providers = set()

        # Load from dict
        if isinstance(definition, dict):
            self._path = None

        # Load from file
        else:
            self._path = fsdecode(definition)
            definition = yaml_read(self._path)

        # Validate content
        self._definition = self._validate(definition)

        # Cache definition for each provider
        self._provider_definition = self._create_provider_definitions()

    def __getitem__(self, key):
        # Get global definition
        if key in FORMAT:
            return self._definition[key]

        # Get provider cached definition, or default definition
        return self._provider_definition.get(
            key, self._provider_definition[None])

    @classmethod
    def from_id(cls, application):
        """
        Load application from Accelize web service.

        Args:
            application (str): Application if format "product_id:version" or
                "product_id".

        Returns:
            Application: Application definition.
        """
        # Get product ID and version
        try:
            product_id, version = application.split(':', 1)
        except ValueError:
            product_id = application
            version = None

        # Get definition from server
        response = request.query('/auth/getapplicationdefinition/',
                                 dict(product_id=product_id, version=version))
        return cls(response)

    @staticmethod
    def list(prefix=''):
        """
        List available applications on Accelize web service.

        Args:
            product_id (str): Product ID linked to the application.
            prefix (str): Product ID prefix to filter.

        Returns:
            list of str: products.
        """
        return request.query('/auth/listapplicationdefinitions/',
                             dict(prefix=prefix))

    @staticmethod
    def list_versions(product_id, prefix=''):
        """
        List available applications on Accelize web service.

        Args:
            product_id (str): Product ID linked to the application.
            prefix (str): Version prefix to filter.

        Returns:
            list of str: versions.
        """
        return request.query('/auth/listapplicationdefinitionversions/',
                             dict(product_id=product_id, prefix=prefix))

    def push(self):
        """
        Push application definition on Accelize web service.
        """
        return request.query('/auth/pushapplicationdefinition/',
                             self._definition, 'post')

    @property
    def providers(self):
        """
        Providers specified in definition.

        Returns:
            set of str: Providers
        """
        return self._providers

    def _create_provider_definitions(self):
        """
        Create cached definition for each provider + a default unspecified
        provider.

        Returns:
            dict: Definition
        """
        result = dict()
        for provider in list(self._providers) + [None]:
            result[provider] = provider_definition = dict()

            for section in self._definition:
                node = self._definition[section]

                if isinstance(node, dict):
                    provider_definition[section] = self._get_provider_node(
                        node, provider)
                else:
                    provider_definition[section] = [
                        self._get_provider_node(node[i], provider)
                        for i in range(len(node))]

        return result

    def _get_provider_node(self, node, provider):
        """
        Get node for a specific provider.

        Args:
            node (dict): Node.
            provider (str or None): provider.

        Returns:
            dict: Node
        """
        result_node = node.copy()

        # Update node with provider specific values
        try:
            result_node.update(node[provider])
        except KeyError:
            pass

        # Clean up other Providers
        for key in self._providers:
            try:
                del result_node[key]
            except KeyError:
                pass

        return result_node

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

            definition[section_name] = self._validate_section(
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

        Returns:
            dict or list: section.
        """
        if not isinstance(section, node_type):
            if node_type == dict:
                raise ConfigurationException(
                    f'The section "{section_name}" must be a "mapping".')
            else:
                section = [section]

        if section_name == 'package' and not section:
            raise ConfigurationException(
                f'The section "{section_name}" must contain a least one '
                f'"mapping".')

        for node in (section if isinstance(section, list) else (section,)):
            args = (node, section_format, section_name)
            self._validate_node(*args)
            if not self._validate_provider_node(*args):
                self._check_required(*args)

        return section

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
        Check for required value in default provider.

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

            # Check required value for default provider
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
        # Check list of values
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

            # Bad value in list
            elif value is not None:
                raise ConfigurationException(
                    f'The "{key}" key in "{section_name}" section must be a '
                    f'list of "{value_type[1].__name__}".')

        # Check single value type
        elif value is not None and not isinstance(value, value_type):
            raise ConfigurationException(
                f'The "{key}" key in "{section_name}" section must be a '
                f'"{value_type.__name__}".')

        valid_values = key_format.get('values')
        valid_regex = key_format.get('regex')

        # Check single value in allowed values
        if valid_values and not (
                value in valid_values or value == key_format.get('default')):
            raise ConfigurationException(
                f'Invalid value "{value}" for "{key}" key in "{section_name}" '
                f'section (possibles values are '
                f'{", ".join(str(valid_value) for valid_value in valid_values)}'
                ').')

        # Check single value match regex
        elif valid_regex and value and not fullmatch(valid_regex, value):
            raise ConfigurationException(
                f'Invalid value "{value}" for "{key}" key in "{section_name}" '
                f'section '
                f'({key_format.get("regex_help", "See documentation")}).')

        return value

    def _validate_provider_node(self, node, node_format, section_name):
        """
        Validate an provider override node.

        Args:
            node (dict): Node to validate
            node_format (dict): Node format
            section_name (str): Parent section name.

        Raises:
            ValueError: Error in node format.

        Returns:
            bool: True in at least one provider found.
        """
        provider_found = False
        for provider in node:

            # Not an provider
            if provider in node_format:
                continue

            if provider in FORMAT:
                raise ConfigurationException(
                    f'Provider in "{section_name}" section cannot be named with'
                    f' reserved name "{provider}".')

            # Provider found
            self._providers.add(provider)
            provider_found = True
            provider_node = node[provider]

            # Provider that is not a dict is likely an unknown key
            if not isinstance(provider_node, dict) or provider_node == '_node':
                raise ConfigurationException(
                    f'Unknown "{provider_node}" key in '
                    f'"{section_name}" section.')

            # Check provider integrity
            for key in node_format:

                if key == '_node':
                    continue

                value = provider_node.get(key, node.get(key))
                key_format = node_format[key]

                # Required value for provider
                if key_format.get('required', False) and value is None:
                    raise ConfigurationException(
                        f'The "{key}" key in "{section_name}" section is '
                        f'required for "{provider}" provider.')

                # Check value
                if key in provider_node:
                    provider_node[key] = Application._check_value(
                        key, key_format, value, section_name)

            # Check for unknown keys in provider
            for key in provider_node:
                if key not in node_format or key == '_node':
                    raise ConfigurationException(
                        f'Unknown "{key}" key in "{section_name}" section '
                        f'for "{provider}" provider.')

        return provider_found

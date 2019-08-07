# coding=utf-8
"""Packer configuration"""
from os.path import join

from accelpy._common import recursive_update, no_color, json_read, json_write
from accelpy._hashicorp import Utility


class Packer(Utility):
    """Packer configuration.

    The template is built using sources JSON files found from:

    - Default configuration.
    - User home directory.
    - Current working directory.
    - Directory specified by "user_config" argument.

    If multiples files with the same name are found, the last one found is used.
    Directories are checked in the listed order to allow user to override
    default configuration easily.

    Args:
        config_dir (path-like object): Configuration directory.
    """
    _FILE = __file__
    _EXTS_INCLUDE = ('.json', )
    _EXTS_EXCLUDE = ('.tf.json', '.tfvars.json')

    def __init__(self, config_dir):
        Utility.__init__(self, config_dir)
        self._template = join(self._config_dir, 'template.json')

    def create_configuration(self, provider=None, application_type=None,
                             variables=None, user_config=None):
        """
        Generate packer configuration file.

        Args:
            provider (str): Provider name.
            user_config (path-like object): User configuration directory.
            vars (dict): Terraform input variables.
        """
        # Lazy import, may not be used
        from jinja2 import Environment

        # Get template from this package and user directories
        sources = dict(vars=dict(variables=variables or dict()))

        for name, src_path in self._list_sources(
                provider, application_type, user_config):
            sources[name] = json_read(src_path)

        # Generate the Packer template file
        template = dict()
        for key in sorted(sources):
            recursive_update(template, sources[key])

        # Evaluate variables that contain Jinja templates
        variables = template['variables']
        env = Environment(extensions=['jinja2.ext.loopcontrols'])
        to_clean = set()
        for key in sorted(variables):
            value = variables[key]
            if isinstance(value, str) and '{' in value:
                variables[key] = env.from_string(value).render(variables)

            # Mark for deletion, Packer does not accept non string as variables
            elif not isinstance(value, str):
                to_clean.add(key)

        for key in to_clean:
            del variables[key]

        # Save template
        json_write(template, self._template)

    def build(self, quiet=False):
        """
        Build image.

        Args:
            quiet (bool): If True, hide outputs.

        Returns:
            dict: Packer manifest (Last build only).
        """
        # Build
        self._exec('build', '-color=false' if no_color() else '',
                   self._template, pipe_stdout=quiet)

        # Read manifest file
        manifest = json_read(join(self._config_dir, 'packer-manifest.json'))
        last_run_uuid = manifest['last_run_uuid']
        for build in manifest['builds']:
            if build['packer_run_uuid'] == last_run_uuid:
                return build
        else:
            # Should never raise
            raise RuntimeError(
                f'No packer manifest for run with UUID {last_run_uuid}')

    def validate(self):
        """
        Validate template.

        Raises:
            project.exceptions.RuntimeException: Error in template.
        """
        self._exec('validate', self._template, pipe_stdout=True)

    @staticmethod
    def get_artifact(manifest):
        """
        Get the image from packer artifact.

        Args:
            manifest (dict): Build manifest.

        Returns:
            str: image.
        """
        builder_type = manifest['builder_type']

        # Builders that returns files
        if builder_type in ('file', ):
            return manifest['files'][0]['name']

        # AWS returns AMI ID
        elif builder_type == 'amazon-ebs':
            return manifest['artifact_id'].split(':', 1)[-1]

        # By default, return artifact ID
        return manifest['artifact_id']

# coding=utf-8
"""Terraform configuration"""
from os.path import join

from accelpy._common import recursive_update, json_read, json_write, no_color
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
        provider (str): Provider name.
        user_config (path-like object): User configuration directory.
        variables (dict): Packer template variables.
    """
    _FILE = __file__
    _EXTS_INCLUDE = ('.json', )
    _EXTS_EXCLUDE = ('.tf.json', '.tfvars.json')

    def __init__(self, *args, **kwargs):
        Utility.__init__(self, *args, **kwargs)
        self._template = join(self._config_dir, 'template.json')

    def create_configuration(self):
        """
        Generate packer configuration file.
        """
        # Get template from this package and user directories
        sources = dict(vars=dict(variables=self._variables))

        for name, src_path in self._list_sources():
            sources[name] = json_read(src_path)

        # Generate the Packer template file
        template = dict()
        for key in sorted(sources):
            recursive_update(template, sources[key])

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

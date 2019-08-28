#! /usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# coding=utf-8
"""Command line interface"""


def _host(args, init=False, **kwargs):
    """
    Return Host instance.

    Args:
        args (argparse.Namespace): CLI arguments.
        kwargs: accelpy._host.Host keyword arguments.

    Returns:
        accelpy._host.Host: Host instance.
    """
    from os.path import join, isfile, isdir

    from accelpy import Host
    from accelpy._common import HOME_DIR

    name = args.name
    latest_path = join(HOME_DIR, 'hosts/latest')

    if init:
        # Create a new configuration
        kwargs.update(dict(application=args.application, provider=args.provider,
                           user_config=args.user_config))
    else:
        # Load an existing configuration
        if not name and isfile(latest_path):
            # Use latest used name if "--name" not specified
            with open(latest_path, 'rt') as latest_file:
                latest = latest_file.read()

            if isdir(join(HOME_DIR, 'hosts', latest)):
                name = latest

        if not name:
            raise OSError(f'A new configuration needs to be created first with '
                          f'"init", or an existing configuration must be '
                          f'specified with "--name".')

        elif name and not isdir(join(HOME_DIR, 'hosts', name)):
            raise OSError(f'No configuration named "{name}".')

    # Create host object
    host = Host(name=name, **kwargs)

    if not name:
        print(host.name)

    # Save name as latest used name
    with open(latest_path, 'wt') as latest_file:
        latest_file.write(host.name)

    return host


def _action_init(args):
    """
    accelpy._host.Host instantiation

    Args:
        args (argparse.Namespace): CLI arguments.
    """
    _host(args, init=True)


def _action_plan(args):
    """
    accelpy._host.Host.plan

    Args:
        args (argparse.Namespace): CLI arguments.

    Returns:
        str: command output.
    """
    return _host(args).plan()


def _action_apply(args):
    """
    accelpy._host.Host.apply

    Args:
        args (argparse.Namespace): CLI arguments.
    """
    host = _host(args)
    host.apply(quiet=args.quiet)
    if not args.quiet:
        from accelpy._common import color_str
        arg = (f' -i $(accelpy ssh_private_key -n {host.name})'
               if host.ssh_private_key else '')
        print(color_str(
            "\nYou can connect to the host using the following command:\n"
            f"ssh -Yt{arg} $(accelpy ssh_user -n {host.name})@"
            f"$(accelpy public_ip -n {host.name})", 'CYAN'))


def _action_build(args):
    """
    accelpy._host.Host.build

    Args:
        args (argparse.Namespace): CLI arguments.

    Returns:
        str: command output.
    """
    return _host(args).build(
        update_application=args.update_application, quiet=args.quiet)


def _action_destroy(args):
    """
    accelpy._host.Host.destroy

    Args:
        args (argparse.Namespace): CLI arguments.
    """
    return _host(args, keep_config=not args.delete).destroy(quiet=args.quiet)


def _action_ssh_private_key(args):
    """
    accelpy._host.ssh_private_key.

    Args:
        args (argparse.Namespace): CLI arguments.

    Returns:
        str: command output.
    """
    return _host(args).ssh_private_key


def _action_ssh_user(args):
    """
    accelpy._host.Host.ssh_user

    Args:
        args (argparse.Namespace): CLI arguments.

    Returns:
        str: command output.
    """
    return _host(args).ssh_user


def _action_private_ip(args):
    """
    accelpy._host.Host.private_ip

    Args:
        args (argparse.Namespace): CLI arguments.

    Returns:
        str: command output.
    """
    return _host(args).private_ip


def _action_public_ip(args):
    """
    accelpy._host.Host.public_ip

    Args:
        args (argparse.Namespace): CLI arguments.

    Returns:
        str: command output.
    """
    return _host(args).public_ip


def _action_list(_):
    """
    Return a list of hosts.

    Returns:
        str: Hosts list.
    """
    from accelpy._host import _iter_hosts_names
    return '\n'.join(_iter_hosts_names())


def _action_lint(args):
    """
    Lint application definition.

    Args:
        args (argparse.Namespace): CLI arguments.
    """
    from accelpy._application import Application
    Application(args.file)


def _action_push(args):
    """
    Push application definition.

    Args:
        args (argparse.Namespace): CLI arguments.
    """
    from accelpy._application import Application
    Application(args.file).push()


def _completer_warn(message):
    """
    Show warning when autocompleting.

    Args:
        message (str): message
    """
    from argcomplete import warn
    from accelpy._common import warn as warn_color
    warn(warn_color(message))


def _yaml_completer(prefix, parsed_args, **__):
    """
    Autocomplete YAML and directories paths.

    Args:
        prefix (str): Application prefix to filter.
        parsed_args (argparse.Namespace): CLI arguments.

    Yields:
        str: path
    """
    from os import listdir
    from os.path import join, isdir, splitext

    try:
        prefix, file_prefix = prefix.rsplit('/', 1)
    except ValueError:
        file_prefix = prefix
        prefix = '.'

    if isdir(prefix):
        for name in listdir(prefix):
            if not name.startswith(file_prefix):
                continue

            path = join(prefix, name) if prefix != '.' else name

            if isdir(path):
                yield path + '/'
            elif splitext(name)[1].lower() in ('.yml', '.yaml'):
                yield path


def _get_cached_app(prefix, name, after, getter):
    """
    Get from cache if available, else get from web server.

    Args:
        prefix (str): Application prefix to filter.
        name (str): Cache name to use.
        after (iterable): Iterable after which chain .
        getter (function): Function ot use to get from web server.

    Returns:
        iterable of str:
    """
    from itertools import chain
    from accelpy._common import get_cli_cache, set_cli_cache

    cached = f'{name}|{prefix}'
    values = get_cli_cache(cached, recursive=True)

    # If no cached values, get from web server then cache values
    if not values:
        values = set_cli_cache(cached, list(getter(prefix)))

    # If cached values, filter before return
    else:
        values = (value for value in values if value.startswith(prefix))

    return chain(after, values)


def _get_product_ids(prefix):
    """
    Get products IDs from web server.

    Args:
        prefix (str): Application prefix to filter.

    Returns:
        list of str: Product ids.
    """
    from accelpy._application import Application
    return Application.list(prefix)


def _get_versions(prefix):
    """
    Get versions from web server.

    Args:
        prefix (str): Application prefix to filter.

    Returns:
        list of str: Versions.
    """
    from accelpy._application import Application
    product_id, version_prefix = prefix.split(':', 1)
    return (f"{product_id}:{version}" for version in
            Application.list_versions(product_id, version_prefix))


def _application_completer(prefix, parsed_args, **__):
    """
    Autocomplete "accelpy init --application"

    Args:
        prefix (str): Application prefix to filter.
        parsed_args (argparse.Namespace): CLI arguments.

    Returns:
        list of str: applications
    """
    # First get local application definitions files
    yaml_applications = _yaml_completer(prefix, parsed_args)

    # If not 100% sure the application is a local file, get applications from
    # the web service, but avoid to call it every time for performance reason.
    # - Only path should starts with "." or "/"
    # - Product ID is in format "vendor/library/name" should not contain more
    #   than 2 "/"
    if (prefix.startswith('.') or prefix.startswith('/') or
            prefix.count('/') > 2):
        return yaml_applications

    # "product_id:version" formatted
    if ':' in prefix:
        name = 'version'
        getter = _get_versions

    # "product_id" formatted
    else:
        name = 'product'
        getter = _get_product_ids

    # Get from server or cache
    from accelpy.exceptions import AuthenticationException
    try:
        return _get_cached_app(prefix, name, yaml_applications, getter)

    except AuthenticationException as exception:
        _completer_warn(
            '"--application"/"-a" argument autocompletion require '
            f'Accelize authentication: {exception}')


def _provider_completer(prefix, parsed_args, **_):
    """
    Autocomplete "accelpy init --provider"

    Args:
        prefix (str): Provider prefix to filter.
        parsed_args (argparse.Namespace): CLI arguments.

    Returns:
        list of str: providers
    """
    application = parsed_args.application
    if application is None:
        _completer_warn('Set "--application"/"-a" argument first to allow '
                        '"--provider"/"-p" argument autocompletion.')
        return

    # First try to get providers from cache
    from os.path import isfile, abspath
    from accelpy._common import get_cli_cache, set_cli_cache

    application = abspath(application) if isfile(application) else application
    cached = f'providers|{application}'
    providers = get_cli_cache(cached)

    # Else get providers from application and cache them
    if not providers:
        from accelpy._application import Application
        providers = Application(application).providers
        set_cli_cache(cached, list(providers))

    # Filter with prefix
    return (provider for provider in providers if provider.startswith(prefix))


def _run_command():
    """
    Command line entry point
    """
    from os import environ
    from argparse import ArgumentParser
    from argcomplete import autocomplete
    from argcomplete.completers import ChoicesCompleter

    # Mark as CLI before import accelpy
    environ['ACCELPY_CLI'] = 'True'
    from accelpy import __version__ as accelpy_version
    from accelpy._host import _iter_hosts_names
    from accelpy._common import warn

    # List existing hosts and eventually generate "init" warning
    names = tuple(_iter_hosts_names())
    names_completer = ChoicesCompleter(names)

    if not names and not environ.get('ACCELPY_GENERATE_CLI_DOC'):
        epilog = warn('No host configuration found, run "accelpy init" first.')
    else:
        epilog = None

    # Parser: "accelpy"
    parser = ArgumentParser(
        prog='accelpy', description=f'Accelpy {accelpy_version}.',
        epilog=epilog)
    sub_parsers = parser.add_subparsers(
        dest='action', title='Commands',
        help='accelpy commands', description=
        'accelpy must perform one of the following commands:')

    # Parser: "accelpy init"
    description = 'Create a new configuration.'
    action = sub_parsers.add_parser(
        'init', help=description, description=description)
    action.add_argument(
        '--name', '-n', help='Name of the configuration to create, if not '
                             'specified a random name is generated. The '
                             'generated name is returned as command output.')
    action.add_argument(
        '--application', '-a',
        help='Application in format '
             '"product_id:version" (or "product_id" for latest version) or '
             'path to a local application definition file.'
    ).completer = _application_completer
    action.add_argument(
        '--provider', '-p', help='Provider name.'
    ).completer = _provider_completer
    action.add_argument(
        '--user_config', '-c',
        help='Extra user configuration directory. Always also use the '
             '"~./accelize" directory.')

    name_help = 'Configuration name to use.'
    # Parser: "accelpy plan"
    description = 'Plan the host infrastructure creation and show details.'
    action = sub_parsers.add_parser('plan', help=description,
                                    description=description, epilog=epilog)
    action.add_argument(
        '--name', '-n', help=name_help).completer = names_completer

    # Parser: "accelpy apply"
    description = 'Create the host infrastructure.'
    action = sub_parsers.add_parser(
        'apply', help=description, description=description, epilog=epilog)
    action.add_argument(
        '--name', '-n', help=name_help).completer = names_completer
    action.add_argument(
        '--quiet', '-q', action='store_true',
        help='If specified, hide outputs.')

    # Parser: "accelpy build"
    description = 'Create a virtual machine image of the configured host.'
    action = sub_parsers.add_parser(
        'build', help=description, description=description, epilog=epilog)
    action.add_argument(
        '--name', '-n', help=name_help).completer = names_completer
    action.add_argument(
        '--update_application', '-u', action='store_true',
        help='If applicable, update the application definition Yaml file to '
             'use this image as host base for the selected provider. Warning, '
             'this will reset any yaml file formatting and comments.')
    action.add_argument(
        '--quiet', '-q', action='store_true',
        help='If specified, hide outputs.')

    # Parser: "accelpy destroy"
    description = 'Destroy the host infrastructure.'
    action = sub_parsers.add_parser(
        'destroy', help=description, description=description, epilog=epilog)
    action.add_argument(
        '--name', '-n', help=name_help).completer = names_completer
    action.add_argument(
        '--quiet', '-q', action='store_true',
        help='If specified, hide outputs.')
    action.add_argument(
        '--delete', '-d', action='store_true',
        help='Delete configuration after command completion.')

    # Parser: "accelpy ssh_private_key"
    description = 'Print the host SSH private key path.'
    action = sub_parsers.add_parser(
        'ssh_private_key', help=description, description=description,
        epilog=epilog)
    action.add_argument(
        '--name', '-n', help=name_help).completer = names_completer

    # Parser: "accelpy ssh_user"
    description = 'Print the name of the user to use to connect with SSH'
    action = sub_parsers.add_parser(
        'ssh_user', help=description, description=description, epilog=epilog)
    action.add_argument(
        '--name', '-n', help=name_help).completer = names_completer

    # Parser: "accelpy private_ip"
    description = 'Print the private IP address.'
    action = sub_parsers.add_parser(
        'private_ip', help=description, description=description, epilog=epilog)
    action.add_argument(
        '--name', '-n', help=name_help).completer = names_completer

    # Parser: "accelpy public_ip"
    description = 'Print the public IP address.'
    action = sub_parsers.add_parser(
        'public_ip', help=description, description=description, epilog=epilog)
    action.add_argument(
        '--name', '-n', help=name_help).completer = names_completer

    # Parser: "accelpy list"
    description = 'List available host configurations.'
    sub_parsers.add_parser(
        'list', help=description, description=description)

    # Parser: "accelpy lint"
    description = 'lint an application definition file.'
    action = sub_parsers.add_parser(
        'lint', help=description, description=description)
    action.add_argument(
        'file', help='Path to YAML file to lint.').completer = _yaml_completer

    # Parser: "accelpy push"
    description = 'Push an application definition file to Accelize web service.'
    action = sub_parsers.add_parser(
        'push', help=description, description=description)
    action.add_argument(
        'file', help='Path to YAML file to push.').completer = _yaml_completer

    # Enable autocompletion
    autocomplete(parser)

    # Get arguments and call function
    args = parser.parse_args()
    action = args.action
    if not action:
        from accelpy._common import error
        parser.error(error('A command is required.'))

    # Disables Python warnings
    from warnings import filterwarnings
    filterwarnings("ignore")

    # Adds parent directory to sys.path:
    # Allows import of accelpy if this script is run locally
    from os.path import dirname, realpath
    import sys
    sys.path.insert(0, dirname(dirname(realpath(__file__))))

    # Run command
    from accelpy.exceptions import AccelizeException
    try:
        output = globals()[f'_action_{action}'](args)
        if output:
            print(output)
        parser.exit()

    except (AccelizeException, OSError) as exception:
        from accelpy._common import debug, error
        if not debug():
            message = str(exception).split('\n', 1)
            message[0] = error(message[0])
            parser.error('\n'.join(message))
        raise

    except KeyboardInterrupt:  # pragma: no cover
        parser.exit(status=1, message="Interrupted by user\n")


if __name__ == '__main__':
    _run_command()

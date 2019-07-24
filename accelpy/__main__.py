#! /usr/bin/env python3
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

    Returns:
        str: command output.
    """
    return _host(args).apply(quiet=args.quiet)


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

    Returns:
        str: command output.
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
    from accelpy import iter_hosts
    return '\n'.join(host.name for host in iter_hosts())


def _action_lint(args):
    """
    Lint application definition.

    Args:
        args (argparse.Namespace): CLI arguments.

    Returns:
        str: Hosts list.
    """
    from accelpy import lint
    return lint(args.file)


def _run_command():
    """
    Command line entry point
    """
    from argparse import ArgumentParser

    # Creates command line argument parser
    parser = ArgumentParser(
        prog='accelpy',
        description='accelpy command line utility.')

    sub_parsers = parser.add_subparsers(
        dest='action', title='Commands',
        help='accelpy commands', description=
        'accelpy must perform one of the following commands:')

    description = 'Create a new configuration.'
    action = sub_parsers.add_parser(
        'init', help=description, description=description)
    action.add_argument(
        '--name', '-n', help='Name of the configuration to create, if not '
                             'specified a random name is generated. The '
                             'generated name is returned as command output.')
    action.add_argument(
        '--application', '-a',
        help='Path to application definition file.')
    action.add_argument('--provider', '-p', help='Provider name.')
    action.add_argument(
        '--user_config', '-c',
        help='Extra user configuration directory. Always also use the '
             '"~./accelize" directory.')

    name_help = 'Configuration name to use.'
    description = 'Plan the host infrastructure creation and show details.'
    action = sub_parsers.add_parser('plan', help=description,
                                    description=description)
    action.add_argument('--name', '-n', help=name_help)

    description = 'Create the host infrastructure.'
    action = sub_parsers.add_parser(
        'apply', help=description, description=description)
    action.add_argument('--name', '-n', help=name_help)
    action.add_argument(
        '--quiet', '-q', action='store_true',
        help='If specified, hide outputs.')

    description = 'Create a virtual machine image of the configured host.'
    action = sub_parsers.add_parser(
        'build', help=description, description=description)
    action.add_argument('--name', '-n', help=name_help)
    action.add_argument(
        '--update_application', '-u', action='store_true',
        help='If applicable, update the application definition Yaml file to '
             'use this image as host base for the selected provider. Warning, '
             'this will reset any yaml file formatting and comments.')
    action.add_argument(
        '--quiet', '-q', action='store_true',
        help='If specified, hide outputs.')

    description = 'Destroy the host infrastructure.'
    action = sub_parsers.add_parser(
        'destroy', help=description, description=description)
    action.add_argument('--name', '-n', help=name_help)
    action.add_argument(
        '--quiet', '-q', action='store_true',
        help='If specified, hide outputs.')
    action.add_argument(
        '--delete', '-d', action='store_true',
        help='Delete configuration after command completion.')

    description = 'Print the host SSH private key path.'
    action = sub_parsers.add_parser(
        'ssh_private_key', help=description, description=description)
    action.add_argument('--name', '-n', help=name_help)

    description = 'Print the name of the user to use to connect with SSH'
    action = sub_parsers.add_parser(
        'ssh_user', help=description, description=description)
    action.add_argument('--name', '-n', help=name_help)

    description = 'Print the private IP address.'
    action = sub_parsers.add_parser(
        'private_ip', help=description, description=description)
    action.add_argument('--name', '-n', help=name_help)

    description = 'Print the public IP address.'
    action = sub_parsers.add_parser(
        'public_ip', help=description, description=description)
    action.add_argument('--name', '-n', help=name_help)

    description = 'List available host configurations.'
    sub_parsers.add_parser(
        'list', help=description, description=description)

    description = 'lint an application definition file.'
    action = sub_parsers.add_parser(
        'lint', help=description, description=description)
    action.add_argument('file', help='Path to file to lint.')

    # Get arguments and call function
    args = parser.parse_args()
    action = args.action
    if not action:
        parser.error('A command is required.')

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
        from accelpy._common import debug
        if not debug():
            parser.error(str(exception))
        raise

    except KeyboardInterrupt:
        parser.exit(status=1, message="Interrupted by user\n")


if __name__ == '__main__':
    _run_command()
